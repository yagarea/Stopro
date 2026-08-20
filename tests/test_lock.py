"""Tests for stopro.lock: lock time parsing and the lock lifecycle."""

from datetime import datetime, timedelta

import pytest

from helpers import ago, locked_state, make_state, ongoing
from stopro import lock


class TestParseLockTime:

    @pytest.mark.parametrize("raw, expected", [
        ("0", 0),
        ("1", 1),
        ("45", 45),
        ("30s", 30),
        ("0s", 0),
        ("1m", 60),
        ("30m", 1800),
        ("1h", 3600),
        ("4h", 14400),
        ("1d", 86400),
        ("7d", 604800),
        ("30 m", 1800),  # int() tolerates the space before the unit
    ])
    def test_accepts_a_number_with_an_optional_unit(self, raw, expected):
        assert lock.parse_lock_time(raw) == expected

    def test_a_bare_number_means_seconds(self):
        assert lock.parse_lock_time("90") == lock.parse_lock_time("90s")

    @pytest.mark.parametrize("raw", [" 30m", "30m ", "\t15h\n"])
    def test_surrounding_whitespace_is_ignored(self, raw):
        assert lock.parse_lock_time(raw) == lock.parse_lock_time(raw.strip())

    @pytest.mark.parametrize("raw", [
        "",              # nothing at all
        " ",             # whitespace only
        "m",             # unit without a number
        "abc",           # not a number
        "1.5h",          # fractional
        "30M",           # units are case sensitive
        "30w",           # unsupported unit
        "-5",            # negative seconds
        "-5m",           # negative with a unit
        "1e3",           # scientific notation
        "0x10",          # hexadecimal
    ])
    def test_rejects_everything_else(self, raw):
        with pytest.raises(lock.InvalidLockTime):
            lock.parse_lock_time(raw)

    def test_error_quotes_the_offending_value_and_lists_the_units(self):
        with pytest.raises(lock.InvalidLockTime) as error_info:
            lock.parse_lock_time("banana")
        message = str(error_info.value)
        assert "'banana'" in message
        for unit in ("s (seconds)", "m (minutes)", "h (hours)", "d (days)"):
            assert unit in message

    def test_error_keeps_the_raw_value(self):
        with pytest.raises(lock.InvalidLockTime) as error_info:
            lock.parse_lock_time("  banana  ")
        assert error_info.value.value == "  banana  "

    def test_every_documented_unit_is_supported(self):
        assert set(lock.UNIT_MULTIPLIERS) == {"s", "m", "h", "d"}


class TestLock:

    def test_records_the_duration_and_the_moment(self, freeze_now):
        moment = freeze_now(datetime(2024, 5, 1, 9, 0, 0), lock)
        state = lock.lock(make_state(running=True), 1800)
        assert state["lock"]["is_locked"] is True
        assert state["lock"]["locked_for"] == 1800
        assert state["lock"]["locked_since"] == moment.isoformat()

    def test_total_time_locked_accumulates(self):
        state = make_state(total_time_locked=600)
        lock.lock(state, 1800)
        assert state["lock"]["total_time_locked"] == 2400
        lock.lock(state, 60)
        assert state["lock"]["total_time_locked"] == 2460

    def test_mutates_and_returns_the_same_state(self):
        state = make_state()
        assert lock.lock(state, 60) is state

    def test_leaves_the_session_log_untouched(self):
        state = make_state(running=True, log=[ongoing(60)])
        log_before = list(state["log"])
        lock.lock(state, 60)
        assert state["log"] == log_before


class TestUnlock:

    def test_clears_the_lock(self):
        state = lock.unlock(locked_state(locked_for=1800))
        assert state["lock"]["is_locked"] is False
        assert state["lock"]["locked_since"] == 0
        assert state["lock"]["locked_for"] == 0

    def test_keeps_the_lifetime_total(self):
        state = locked_state(locked_for=1800, total_time_locked=7200)
        lock.unlock(state)
        assert state["lock"]["total_time_locked"] == 7200

    def test_lock_then_unlock_round_trips(self):
        state = make_state(running=True)
        lock.lock(state, 300)
        lock.unlock(state)
        assert state["lock"]["is_locked"] is False
        assert state["lock"]["total_time_locked"] == 300


class TestIsLocked:
    """is_locked() deliberately reads the state file rather than a passed state."""

    def test_false_for_an_unlocked_state_file(self, state_file):
        state_file.write(make_state())
        assert lock.is_locked() is False

    def test_true_for_a_locked_state_file(self, state_file):
        state_file.write(locked_state())
        assert lock.is_locked() is True

    def test_creates_a_clean_state_when_there_is_no_file(self, state_file):
        assert not state_file.exists()
        assert lock.is_locked() is False

    def test_ignores_in_memory_changes_that_were_never_saved(self, state_file):
        state_file.write(make_state())
        state = lock.lock(make_state(), 600)
        assert state["lock"]["is_locked"] is True
        assert lock.is_locked() is False


class TestIsUnlockAllowed:

    def test_an_unlocked_session_can_always_be_stopped(self):
        assert lock.is_unlock_allowed(make_state(running=True)) is True

    def test_a_running_lock_blocks_the_stop(self):
        assert lock.is_unlock_allowed(locked_state(locked_for=3600)) is False

    def test_an_expired_lock_releases_the_stop(self):
        state = locked_state(locked_for=60, locked_since_seconds_ago=3600)
        assert lock.is_unlock_allowed(state) is True

    def test_the_boundary_second_still_blocks(self, freeze_now):
        start = datetime(2024, 5, 1, 9, 0, 0)
        state = make_state(is_locked=True, locked_since=start.isoformat(), locked_for=60)
        freeze_now(start + timedelta(seconds=60), lock)
        assert lock.is_unlock_allowed(state) is False

    def test_one_second_past_the_boundary_releases(self, freeze_now):
        start = datetime(2024, 5, 1, 9, 0, 0)
        state = make_state(is_locked=True, locked_since=start.isoformat(), locked_for=60)
        freeze_now(start + timedelta(seconds=61), lock)
        assert lock.is_unlock_allowed(state) is True

    def test_a_zero_length_lock_is_immediately_over(self):
        assert lock.is_unlock_allowed(locked_state(locked_for=0)) is True

    def test_reads_the_timestamp_format_written_by_log_activity(self):
        """lock.lock() writes isoformat, log_activity() writes str(datetime)."""
        state = make_state(
            is_locked=True,
            locked_since=str(datetime.now() - timedelta(hours=2)),
            locked_for=3600,
        )
        assert lock.is_unlock_allowed(state) is True

    def test_debug_dumps_the_lock_fields(self, output):
        state = locked_state(locked_for=1800)
        lock.is_unlock_allowed(state, debug=True)
        printed = output()
        for label in ("Locked since:", "Locked for:", "Total time locked:", "Is locked:"):
            assert label in printed

    def test_quiet_without_debug(self, output):
        lock.is_unlock_allowed(locked_state())
        assert output() == ""


class TestGetRemainingTime:

    def test_counts_down_from_the_full_duration(self):
        state = locked_state(locked_for=1800)
        assert lock.get_remaining_time(state) == pytest.approx(1800, abs=5)

    def test_subtracts_the_elapsed_time(self):
        state = locked_state(locked_for=1800, locked_since_seconds_ago=600)
        assert lock.get_remaining_time(state) == pytest.approx(1200, abs=5)

    def test_goes_negative_once_the_lock_expired(self):
        state = locked_state(locked_for=60, locked_since_seconds_ago=300)
        assert lock.get_remaining_time(state) == pytest.approx(-240, abs=5)

    def test_is_exact_against_a_frozen_clock(self, freeze_now):
        start = datetime(2024, 5, 1, 9, 0, 0)
        freeze_now(start + timedelta(seconds=30), lock)
        state = make_state(is_locked=True, locked_since=start.isoformat(), locked_for=100)
        assert lock.get_remaining_time(state) == 70.0


class TestProgressBars:

    def test_static_bar_renders_the_remaining_time(self, output, freeze_now):
        start = datetime(2024, 5, 1, 9, 0, 0)
        freeze_now(start + timedelta(seconds=600), lock)
        state = make_state(is_locked=True, locked_since=start.isoformat(), locked_for=3600)
        lock.static_progressbar(state)
        printed = output()
        assert "Lock:" in printed
        assert "50 minutes remaining" in printed

    def test_static_bar_does_not_wait(self, monkeypatch):
        def explode(_seconds):
            raise AssertionError("the static bar must never sleep")
        monkeypatch.setattr(lock, "sleep", explode)
        lock.static_progressbar(locked_state(locked_for=3600))

    def test_blocking_bar_returns_at_once_when_the_lock_expired(self, monkeypatch):
        def explode(_seconds):
            raise AssertionError("nothing left to wait for")
        monkeypatch.setattr(lock, "sleep", explode)
        lock.progressbar(locked_state(locked_for=60, locked_since_seconds_ago=600))

    def test_blocking_bar_waits_out_the_lock_one_second_at_a_time(self, monkeypatch, advancing_now):
        start = datetime(2024, 5, 1, 9, 0, 0)
        state = make_state(is_locked=True, locked_since=start.isoformat(), locked_for=3)
        advancing_now(start, lock)  # every now() call moves one second forward
        slept = []
        monkeypatch.setattr(lock, "sleep", slept.append)
        lock.progressbar(state)
        assert slept == [1, 1, 1]
