"""Tests for stopro.utils: yaml IO, state handling and the hosts file."""

from datetime import datetime

import pytest
import yaml

from helpers import make_state, ongoing
from stopro import utils


class TestLoadYaml:

    def test_returns_parsed_document(self, tmp_path):
        target = tmp_path / "conf.yml"
        target.write_text("forbidden_sites:\n  - example.com\n")
        assert utils.load_yaml(str(target)) == {"forbidden_sites": ["example.com"]}

    def test_empty_file_parses_to_none(self, tmp_path):
        target = tmp_path / "empty.yml"
        target.write_text("")
        assert utils.load_yaml(str(target)) is None

    def test_debug_echoes_source_and_content(self, tmp_path, output):
        target = tmp_path / "conf.yml"
        target.write_text("a: 1\n")
        utils.load_yaml(str(target), debug=True)
        printed = output()
        assert str(target) in printed
        assert "Loaded yaml from" in printed

    def test_quiet_by_default(self, tmp_path, output):
        target = tmp_path / "conf.yml"
        target.write_text("a: 1\n")
        utils.load_yaml(str(target))
        assert output() == ""

    def test_broken_syntax_exits(self, tmp_path, output):
        target = tmp_path / "broken.yml"
        target.write_text("forbidden_sites: [unclosed\n")
        with pytest.raises(SystemExit) as exit_info:
            utils.load_yaml(str(target))
        assert exit_info.value.code == 1
        assert "Yaml parse" in output()

    def test_missing_file_exits(self, tmp_path, output):
        with pytest.raises(SystemExit) as exit_info:
            utils.load_yaml(str(tmp_path / "nope.yml"))
        assert exit_info.value.code == 1
        assert "does not exists" in output()

    def test_unreadable_path_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            utils.load_yaml(str(tmp_path))  # a directory, not a file


class TestWriteYaml:

    def test_round_trips_through_load_yaml(self, tmp_path):
        target = tmp_path / "out.yml"
        content = make_state(running=True, log=[["start", "+"]])
        utils.write_yaml(content, str(target))
        assert utils.load_yaml(str(target)) == content

    def test_serialises_arbitrary_objects_without_complaining(self, tmp_path):
        """yaml.dump() tags unknown objects rather than raising, which is why
        write_yaml's YAMLError branch is unreachable from stopro itself."""
        utils.write_yaml({"state": object()}, str(tmp_path / "out.yml"))
        assert "!!python/object" in (tmp_path / "out.yml").read_text()

    def test_a_dump_error_would_exit(self, tmp_path, monkeypatch, output):
        def explode(_content):
            raise yaml.YAMLError("cannot represent")
        monkeypatch.setattr(utils.yaml, "dump", explode)
        with pytest.raises(SystemExit) as exit_info:
            utils.write_yaml({"a": 1}, str(tmp_path / "out.yml"))
        assert exit_info.value.code == 1
        assert "Yaml parse" in output()

    def test_unwritable_path_exits(self, tmp_path, output):
        with pytest.raises(SystemExit) as exit_info:
            utils.write_yaml({"a": 1}, str(tmp_path / "missing_dir" / "out.yml"))
        assert exit_info.value.code == 1
        assert "Error occurred while writing" in output()


class TestStateDirectory:

    def test_creates_missing_parents(self, paths):
        assert not paths.state.parent.exists()
        utils.create_state_directory()
        assert paths.state.parent.is_dir()

    def test_is_idempotent(self, paths):
        utils.create_state_directory()
        utils.create_state_directory()
        assert paths.state.parent.is_dir()

    def test_relative_state_path_needs_no_directory(self, monkeypatch, tmp_path):
        monkeypatch.setattr(utils, "STATE_PATH", "state.yml")
        monkeypatch.chdir(tmp_path)
        utils.create_state_directory()
        assert not (tmp_path / "state.yml").exists()

    def test_failure_to_create_exits(self, monkeypatch, output):
        def explode(*args, **kwargs):
            raise OSError("read-only file system")
        monkeypatch.setattr(utils, "makedirs", explode)
        with pytest.raises(SystemExit) as exit_info:
            utils.create_state_directory()
        assert exit_info.value.code == 1
        assert "Could not create state directory" in output()


class TestCleanState:

    def test_has_the_documented_shape(self):
        clean = utils.create_new_clean_state()
        assert clean == {
            "log": [],
            "running": False,
            "lock": {
                "is_locked": False,
                "locked_for": 0,
                "locked_since": 0,
                "total_time_locked": 0,
            },
        }

    def test_is_written_to_the_state_file(self, state_file):
        returned = utils.create_new_clean_state()
        assert state_file.read() == returned

    def test_overwrites_previous_history(self, state_file):
        state_file.write(make_state(log=[["a", "b"], ["c", "d"]], total_time_locked=99))
        utils.create_new_clean_state()
        assert state_file.read()["log"] == []
        assert state_file.read()["lock"]["total_time_locked"] == 0


class TestGetState:

    def test_creates_a_clean_state_when_the_file_is_missing(self, state_file):
        assert not state_file.exists()
        assert utils.get_state()["running"] is False
        assert state_file.exists()

    def test_reads_an_existing_state_file(self, state_file):
        stored = state_file.write(make_state(running=True, total_time_locked=42))
        assert utils.get_state() == stored

    def test_result_is_cached(self, state_file):
        state_file.write(make_state())
        assert utils.get_state() is utils.get_state()

    def test_cache_hides_later_edits_until_cleared(self, state_file):
        state_file.write(make_state(running=False))
        assert utils.get_state()["running"] is False
        state_file.write(make_state(running=True))  # write() clears the cache
        assert utils.get_state()["running"] is True

    def test_debug_argument_is_part_of_the_cache_key(self, state_file):
        state_file.write(make_state())
        assert utils.get_state() is not utils.get_state(debug=True)


class TestSaveState:

    def test_writes_the_state_verbatim(self, state_file):
        state = state_file.write(make_state())
        state["running"] = True
        state["log"] = [ongoing(60)]
        utils.save_state(state)
        assert state_file.read() == state


class TestStateWritesNeedTheDirectory:
    """save_state()/log_activity() write straight to STATE_PATH.

    Only get_state() ever creates the directory, so a state directory that
    disappears mid-session takes the process down with an error.
    """

    def test_save_state_exits_when_the_directory_is_gone(self, output):
        with pytest.raises(SystemExit) as exit_info:
            utils.save_state(make_state())
        assert exit_info.value.code == 1
        assert "Error occurred while writing" in output()

    def test_get_state_first_makes_the_write_succeed(self, state_file):
        state = utils.get_state()
        utils.save_state(state)
        assert state_file.read() == state


class TestLogActivity:

    def test_starting_opens_a_new_entry(self, state_file, freeze_now):
        moment = freeze_now(datetime(2024, 5, 1, 8, 0, 0), utils)
        state = state_file.write(make_state(running=False))
        utils.log_activity(state)
        assert state["running"] is True
        assert state["log"] == [[str(moment), "+"]]
        assert state_file.read() == state

    def test_stopping_closes_the_open_entry(self, state_file, freeze_now):
        moment = freeze_now(datetime(2024, 5, 1, 12, 0, 0), utils)
        state = state_file.write(make_state(running=True, log=[["2024-05-01 08:00:00", "+"]]))
        utils.log_activity(state)
        assert state["running"] is False
        assert state["log"] == [["2024-05-01 08:00:00", str(moment)]]
        assert state_file.read() == state

    def test_earlier_sessions_are_left_alone(self, state_file):
        state = state_file.write(make_state(running=True, log=[["a", "b"], ["c", "+"]]))
        utils.log_activity(state)
        assert state["log"][0] == ["a", "b"]
        assert state["log"][1][1] != "+"

    def test_stopping_without_history_reports_corruption(self, state_file, output, freeze_now):
        moment = freeze_now(datetime(2024, 5, 1, 12, 0, 0), utils)
        state = state_file.write(make_state(running=True, log=[]))
        utils.log_activity(state)
        assert "log corrupted" in output()
        assert state["log"] == [["?", str(moment)]]
        assert state["running"] is False

    def test_start_stop_start_leaves_two_entries(self, state_file):
        state = state_file.write(make_state())
        utils.log_activity(state)
        utils.log_activity(state)
        utils.log_activity(state)
        assert len(state["log"]) == 2
        assert state["log"][0][1] != "+"
        assert state["log"][1][1] == "+"
        assert state["running"] is True


class TestHostsBackup:

    def test_backup_copies_the_hosts_file(self, hosts_file, original_hosts):
        utils.backup_hosts()
        assert hosts_file.has_backup
        assert hosts_file.backup_path.read_text() == original_hosts

    def test_backup_overwrites_a_previous_one(self, hosts_file):
        hosts_file.write_backup("stale\n")
        hosts_file.write("fresh\n")
        utils.backup_hosts()
        assert hosts_file.backup_path.read_text() == "fresh\n"

    def test_apply_backup_restores_and_consumes_the_backup(self, hosts_file, original_hosts):
        utils.backup_hosts()
        hosts_file.write(original_hosts + "0.0.0.0 example.com\n")
        assert utils.apply_backup() is True
        assert hosts_file.read() == original_hosts
        assert not hosts_file.has_backup

    def test_apply_backup_without_a_backup_is_a_noop(self, hosts_file, original_hosts):
        assert utils.apply_backup() is False
        assert hosts_file.read() == original_hosts

    def test_apply_backup_reports_a_failed_move(self, monkeypatch, hosts_file, output):
        utils.backup_hosts()

        def explode(*args, **kwargs):
            raise OSError("device busy")
        monkeypatch.setattr(utils, "move", explode)
        assert utils.apply_backup() is False
        assert "Could not restore" in output()


class TestHostsBlocking:

    def test_forbid_sites_adds_four_rules_per_site(self, hosts_file, original_hosts):
        utils.forbid_sites(["example.com", "example.org"])
        content = hosts_file.read()
        assert content.startswith(original_hosts)
        assert utils.BLOCK_MARKER in content
        for site in ("example.com", "example.org"):
            assert f"0.0.0.0 {site}\n" in content
            assert f"0.0.0.0 www.{site}\n" in content
            assert f"::0 {site}\n" in content
            assert f"::0 www.{site}\n" in content

    def test_forbid_sites_with_an_empty_list_only_adds_the_marker(self, hosts_file, original_hosts):
        utils.forbid_sites([])
        assert hosts_file.read() == f"{original_hosts}\n\n{utils.BLOCK_MARKER}\n"

    def test_is_hosts_blocked_detects_the_marker(self, hosts_file):
        assert utils.is_hosts_blocked() is False
        utils.forbid_sites(["example.com"])
        assert utils.is_hosts_blocked() is True

    def test_is_hosts_blocked_is_false_without_a_hosts_file(self, paths):
        paths.hosts.unlink()
        assert utils.is_hosts_blocked() is False

    def test_block_then_restore_leaves_hosts_untouched(self, hosts_file, original_hosts):
        utils.backup_hosts()
        utils.forbid_sites(["example.com"])
        utils.apply_backup()
        assert hosts_file.read() == original_hosts
        assert utils.is_hosts_blocked() is False


class TestFormatSecond:

    @pytest.mark.parametrize("seconds, expected", [
        (0, "0 seconds"),
        (1, "1 second"),
        (2, "2 seconds"),
        (59, "59 seconds"),
        (60, "1 minute"),
        (61, "1 minute 1 second"),
        (120, "2 minutes"),
        (3600, "1 hour"),
        (3661, "1 hour 1 minute 1 second"),
        (7200, "2 hours"),
        (86400, "1 day"),
        (86460, "1 day 1 minute"),
        (90061, "1 day 1 hour 1 minute 1 second"),
        (172800, "2 days"),
    ])
    def test_known_durations(self, seconds, expected):
        assert utils.format_second(seconds) == expected

    def test_zero_units_are_skipped(self):
        assert "hour" not in utils.format_second(86460)

    def test_fractions_are_truncated(self):
        assert utils.format_second(90.5) == "1 minute 30 seconds"

    def test_float_zero_is_still_zero_seconds(self):
        assert utils.format_second(0.0) == "0 seconds"

    def test_result_is_never_padded(self):
        for seconds in (0, 1, 60, 3600, 86400, 90061):
            formatted = utils.format_second(seconds)
            assert formatted == formatted.strip()


class TestPrintError:

    def test_prefixes_the_message(self, output):
        utils.print_error("something went wrong")
        assert output() == "ERROR: something went wrong"

    def test_renders_rich_markup_away(self, output):
        utils.print_error("check /etc/hosts")
        assert "[bold red]" not in output()
