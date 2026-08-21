"""Tests for stopro.state.State: loading, saving and every change to the state.

The on-disk format is older than the class and must not drift, so most of these
assert against the state file itself rather than against the attributes.
"""

from datetime import datetime, timedelta

import pytest
import yaml

from helpers import as_state, locked_state, make_state, ongoing, session
from stopro import state as state_module
from stopro.state import State


CLEAN_FILE = {
    "log": [],
    "running": False,
    "lock": {"is_locked": False, "locked_for": 0,
             "locked_since": 0, "total_time_locked": 0},
}


class TestFileFormat:
    """The file format predates the class; attribute names may differ from keys."""

    def test_a_clean_state_matches_the_documented_file(self):
        assert State().as_dict() == CLEAN_FILE

    def test_the_running_flag_is_stored_under_its_old_key(self):
        stored = State(is_running=True).as_dict()
        assert stored["running"] is True
        assert "is_running" not in stored

    def test_from_dict_reads_every_field(self):
        state = State.from_dict(make_state(
            running=True, log=[["a", "b"]], is_locked=True,
            locked_since="2024-05-01T09:00:00", locked_for=1800, total_time_locked=5400))
        assert state.log == [["a", "b"]]
        assert state.is_running is True
        assert state.is_locked is True
        assert state.locked_since == "2024-05-01T09:00:00"
        assert state.locked_for == 1800
        assert state.total_time_locked == 5400

    def test_from_dict_and_as_dict_round_trip(self):
        stored = make_state(running=True, log=[session(7200, 3600)], is_locked=True,
                            locked_since="2024-05-01T09:00:00", locked_for=60,
                            total_time_locked=900)
        assert State.from_dict(stored).as_dict() == stored

    def test_load_and_save_leave_the_file_untouched(self, state_file):
        stored = state_file.write(make_state(running=True, log=[ongoing(600)],
                                             total_time_locked=42))
        before = state_file.path.read_text()
        State.load().save()
        assert state_file.path.read_text() == before
        assert state_file.read() == stored


class TestLoad:

    def test_reads_an_existing_state_file(self, state_file):
        stored = state_file.write(make_state(running=True, total_time_locked=42))
        state = State.load()
        assert state.is_running is True
        assert state.total_time_locked == 42
        assert state.as_dict() == stored

    def test_creates_a_clean_state_when_the_file_is_missing(self, state_file):
        assert not state_file.exists()
        state = State.load()
        assert state.as_dict() == CLEAN_FILE
        assert state_file.read() == CLEAN_FILE

    def test_creates_the_state_directory_too(self, paths):
        assert not paths.state.parent.exists()
        State.load()
        assert paths.state.is_file()

    def test_uses_the_configured_state_path(self, state_file):
        state_file.write(make_state(running=True))
        assert State.load().path == str(state_file.path)

    def test_an_explicit_path_wins(self, tmp_path, state_file):
        state_file.write(make_state(running=True))
        elsewhere = tmp_path / "other.yml"
        elsewhere.write_text(yaml.dump(make_state(running=False, total_time_locked=7)))
        state = State.load(str(elsewhere))
        assert state.is_running is False
        assert state.total_time_locked == 7

    def test_each_load_is_independent(self, state_file):
        """No cache: two loads give two objects, so one can not shadow the other."""
        state_file.write(make_state())
        first, second = State.load(), State.load()
        assert first is not second
        first.is_running = True
        assert second.is_running is False

    def test_a_later_load_sees_what_was_saved(self, state_file):
        state = State.load()
        state.start()
        assert State.load().is_running is True

    def test_a_broken_state_file_exits(self, state_file, output):
        state_file.path.parent.mkdir(parents=True, exist_ok=True)
        state_file.path.write_text("log: [unclosed\n")
        with pytest.raises(SystemExit) as exit_info:
            State.load()
        assert exit_info.value.code == 1
        assert "Yaml parse" in output()

    def test_debug_echoes_the_file_and_the_state(self, state_file, output):
        state_file.write(make_state(running=True, total_time_locked=99))
        State.load(debug=True)
        printed = output()
        assert "Loaded yaml from" in printed
        assert "is_running=True" in printed
        assert "total_time_locked=99" in printed

    def test_quiet_without_debug(self, state_file, output):
        state_file.write(make_state())
        State.load()
        assert output() == ""


class TestSave:

    def test_writes_the_file(self, state_file):
        State(log=[["a", "b"]], is_running=True).save()
        stored = state_file.read()
        assert stored["running"] is True
        assert stored["log"] == [["a", "b"]]

    def test_creates_a_missing_state_directory(self, paths):
        assert not paths.state.parent.exists()
        State().save()
        assert paths.state.is_file()

    def test_overwrites_a_previous_file(self, state_file):
        state_file.write(make_state(running=True, log=[ongoing(60)]))
        State().save()
        assert state_file.read() == CLEAN_FILE

    def test_saves_where_the_state_was_loaded_from(self, tmp_path, state_file):
        elsewhere = tmp_path / "other.yml"
        elsewhere.write_text(yaml.dump(make_state()))
        state = State.load(str(elsewhere))
        state.start()
        assert yaml.safe_load(elsewhere.read_text())["running"] is True
        assert not state_file.exists()


class TestStart:

    def test_opens_a_session(self, state_file, freeze_now):
        moment = freeze_now(datetime(2024, 5, 1, 8, 0, 0), state_module)
        state = State.load()
        state.start()
        assert state.is_running is True
        assert state.log == [[str(moment), "+"]]

    def test_persists_immediately(self, state_file):
        State.load().start()
        stored = state_file.read()
        assert stored["running"] is True
        assert stored["log"][0][1] == "+"

    def test_keeps_earlier_sessions(self, state_file):
        state = as_state(make_state(log=[session(7200, 3600)]))
        state.start()
        assert len(state.log) == 2
        assert state.log[0][1] != "+"

    def test_without_a_lock_the_session_is_open(self, state_file):
        state = State.load()
        state.start()
        assert state.is_locked is False
        assert state_file.read()["lock"] == CLEAN_FILE["lock"]

    def test_locks_the_session_when_asked(self, state_file, freeze_now):
        moment = freeze_now(datetime(2024, 5, 1, 8, 0, 0), state_module)
        state = State.load()
        state.start(locked_for=1800)
        assert state.is_locked is True
        assert state.locked_for == 1800
        assert state.locked_since == moment.isoformat()
        assert state.total_time_locked == 1800

    def test_a_zero_second_lock_still_counts_as_locked(self, state_file):
        state = State.load()
        state.start(locked_for=0)
        assert state.is_locked is True
        assert state.is_unlock_allowed is True

    def test_one_save_holds_both_the_session_and_the_lock(self, state_file):
        state = State.load()
        state.start(locked_for=60)
        stored = state_file.read()
        assert stored["running"] is True
        assert stored["lock"]["is_locked"] is True


class TestStop:

    def test_closes_the_open_session(self, state_file, freeze_now):
        moment = freeze_now(datetime(2024, 5, 1, 12, 0, 0), state_module)
        state = as_state(make_state(running=True, log=[["2024-05-01 08:00:00", "+"]]))
        state.stop()
        assert state.is_running is False
        assert state.log == [["2024-05-01 08:00:00", str(moment)]]

    def test_persists_immediately(self, state_file):
        state = as_state(make_state(running=True, log=[ongoing(600)]))
        state.stop()
        stored = state_file.read()
        assert stored["running"] is False
        assert stored["log"][-1][1] != "+"

    def test_releases_the_lock(self, state_file):
        state = as_state(locked_state(locked_for=1800))
        state.stop()
        assert state.is_locked is False
        assert state.locked_since == 0
        assert state.locked_for == 0

    def test_keeps_the_lifetime_lock_total(self, state_file):
        state = as_state(locked_state(locked_for=1800, total_time_locked=9000))
        state.stop()
        assert state.total_time_locked == 9000

    def test_earlier_sessions_are_left_alone(self, state_file):
        state = as_state(make_state(running=True, log=[["a", "b"], ["c", "+"]]))
        state.stop()
        assert state.log[0] == ["a", "b"]
        assert state.log[1][1] != "+"

    def test_stopping_without_history_reports_corruption(self, state_file, output, freeze_now):
        moment = freeze_now(datetime(2024, 5, 1, 12, 0, 0), state_module)
        state = as_state(make_state(running=True, log=[]))
        state.stop()
        assert "log corrupted" in output()
        assert state.log == [["?", str(moment)]]
        assert state.is_running is False

    def test_start_stop_start_leaves_two_entries(self, state_file):
        state = State.load()
        state.start()
        state.stop()
        state.start()
        assert len(state.log) == 2
        assert state.log[0][1] != "+"
        assert state.log[1][1] == "+"
        assert state.is_running is True


class TestClear:

    def test_forgets_every_session(self, state_file):
        state = as_state(make_state(log=[session(7200, 3600), session(600, 0)]))
        state.clear()
        assert state.log == []

    def test_resets_the_lifetime_lock_total(self, state_file):
        state = as_state(make_state(total_time_locked=90000))
        state.clear()
        assert state.total_time_locked == 0

    def test_leaves_a_clean_file_behind(self, state_file):
        state = as_state(locked_state(locked_for=1800, total_time_locked=900))
        state.clear()
        assert state_file.read() == CLEAN_FILE


class TestLock:

    def test_records_the_duration_and_the_moment(self, state_file, freeze_now):
        moment = freeze_now(datetime(2024, 5, 1, 9, 0, 0), state_module)
        state = as_state(make_state(running=True))
        state.lock(1800)
        assert state.is_locked is True
        assert state.locked_for == 1800
        assert state.locked_since == moment.isoformat()

    def test_persists_immediately(self, state_file):
        state = as_state(make_state(running=True, log=[ongoing(600)]))
        state.lock(1800)
        assert state_file.read()["lock"]["is_locked"] is True

    def test_total_time_locked_accumulates(self, state_file):
        state = as_state(make_state(total_time_locked=600))
        state.lock(1800)
        assert state.total_time_locked == 2400
        state.lock(60)
        assert state.total_time_locked == 2460

    def test_leaves_the_session_log_untouched(self, state_file):
        state = as_state(make_state(running=True, log=[ongoing(60)]))
        log_before = list(state.log)
        state.lock(60)
        assert state.log == log_before


class TestUnlock:

    def test_clears_the_lock(self, state_file):
        state = as_state(locked_state(locked_for=1800))
        state.unlock()
        assert state.is_locked is False
        assert state.locked_since == 0
        assert state.locked_for == 0

    def test_keeps_the_lifetime_total(self, state_file):
        state = as_state(locked_state(locked_for=1800, total_time_locked=7200))
        state.unlock()
        assert state.total_time_locked == 7200

    def test_persists_immediately(self, state_file):
        state = as_state(locked_state(locked_for=1800))
        state.unlock()
        assert state_file.read()["lock"]["is_locked"] is False

    def test_the_session_keeps_running(self, state_file):
        state = as_state(locked_state(locked_for=1800))
        state.unlock()
        assert state.is_running is True

    def test_lock_then_unlock_round_trips(self, state_file):
        state = as_state(make_state(running=True))
        state.lock(300)
        state.unlock()
        assert state.is_locked is False
        assert state.total_time_locked == 300


class TestIsUnlockAllowed:

    def test_an_unlocked_session_can_always_be_stopped(self):
        assert as_state(make_state(running=True)).is_unlock_allowed is True

    def test_a_running_lock_blocks_the_stop(self):
        assert as_state(locked_state(locked_for=3600)).is_unlock_allowed is False

    def test_an_expired_lock_releases_the_stop(self):
        state = as_state(locked_state(locked_for=60, locked_since_seconds_ago=3600))
        assert state.is_unlock_allowed is True

    def test_the_boundary_second_still_blocks(self, freeze_now):
        start = datetime(2024, 5, 1, 9, 0, 0)
        state = as_state(make_state(is_locked=True, locked_since=start.isoformat(),
                                    locked_for=60))
        freeze_now(start + timedelta(seconds=60), state_module)
        assert state.is_unlock_allowed is False

    def test_one_second_past_the_boundary_releases(self, freeze_now):
        start = datetime(2024, 5, 1, 9, 0, 0)
        state = as_state(make_state(is_locked=True, locked_since=start.isoformat(),
                                    locked_for=60))
        freeze_now(start + timedelta(seconds=61), state_module)
        assert state.is_unlock_allowed is True

    def test_a_zero_length_lock_is_immediately_over(self):
        assert as_state(locked_state(locked_for=0)).is_unlock_allowed is True

    def test_reads_the_timestamp_format_written_by_start(self):
        """lock() writes isoformat, start() writes str(datetime)."""
        state = as_state(make_state(is_locked=True,
                                    locked_since=str(datetime.now() - timedelta(hours=2)),
                                    locked_for=3600))
        assert state.is_unlock_allowed is True

    def test_answers_from_its_own_fields_not_from_the_file(self, state_file):
        """The old lock.is_locked() re-read the file and ignored its argument."""
        state_file.write(make_state())
        assert as_state(locked_state(locked_for=3600)).is_unlock_allowed is False


class TestRemainingLockTime:

    def test_counts_down_from_the_full_duration(self):
        state = as_state(locked_state(locked_for=1800))
        assert state.remaining_lock_time == pytest.approx(1800, abs=5)

    def test_subtracts_the_elapsed_time(self):
        state = as_state(locked_state(locked_for=1800, locked_since_seconds_ago=600))
        assert state.remaining_lock_time == pytest.approx(1200, abs=5)

    def test_goes_negative_once_the_lock_expired(self):
        state = as_state(locked_state(locked_for=60, locked_since_seconds_ago=300))
        assert state.remaining_lock_time == pytest.approx(-240, abs=5)

    def test_is_exact_against_a_frozen_clock(self, freeze_now):
        start = datetime(2024, 5, 1, 9, 0, 0)
        freeze_now(start + timedelta(seconds=30), state_module)
        state = as_state(make_state(is_locked=True, locked_since=start.isoformat(),
                                    locked_for=100))
        assert state.remaining_lock_time == 70.0


class TestRepr:

    def test_names_the_fields_worth_debugging(self):
        state = as_state(locked_state(locked_for=1800, total_time_locked=5400))
        shown = repr(state)
        for field in ("is_running=True", "is_locked=True", "locked_for=1800",
                      "total_time_locked=5400", "locked_since=", "sessions=1"):
            assert field in shown

    def test_summarises_the_log_instead_of_dumping_it(self):
        state = as_state(make_state(log=[session(7200, 3600), session(600, 0)]))
        assert "sessions=2" in repr(state)
        assert "2024" not in repr(state)
