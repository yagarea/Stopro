"""Tests for stopro.commands.

These drive the commands end to end against a temporary hosts file and state
file, so the assertions are about what actually landed on disk.
"""

import pytest

from helpers import (DEFAULT_CONFIG, locked_state, make_args, make_state,
                     ongoing, session)
from stopro import commands, lock, utils
from stopro.state import State


@pytest.fixture
def blocked(hosts_file):
    """Put the machine in the state 'stopro start' leaves behind."""
    utils.backup_hosts()
    utils.forbid_sites(DEFAULT_CONFIG["forbidden_sites"])
    return hosts_file


class TestCmdStart:

    def test_blocks_every_configured_site(self, load_state, hosts_file):
        state = load_state(make_state())
        commands.cmd_start(make_args("start"), DEFAULT_CONFIG, state)
        content = hosts_file.read()
        for site in DEFAULT_CONFIG["forbidden_sites"]:
            assert f"0.0.0.0 {site}" in content
            assert f"0.0.0.0 www.{site}" in content

    def test_backs_up_the_original_hosts_file(self, load_state, hosts_file, original_hosts):
        state = load_state(make_state())
        commands.cmd_start(make_args("start"), DEFAULT_CONFIG, state)
        assert hosts_file.backup_path.read_text() == original_hosts

    def test_opens_a_session_in_the_state_file(self, load_state, state_file):
        state = load_state(make_state())
        commands.cmd_start(make_args("start"), DEFAULT_CONFIG, state)
        stored = state_file.read()
        assert stored["running"] is True
        assert len(stored["log"]) == 1
        assert stored["log"][0][1] == "+"

    def test_announces_the_start(self, load_state, output):
        state = load_state(make_state())
        commands.cmd_start(make_args("start"), DEFAULT_CONFIG, state)
        assert "Your self control session started" in output()

    def test_silent_mode_says_nothing(self, load_state, output):
        state = load_state(make_state())
        commands.cmd_start(make_args("start", silent_mode=True), DEFAULT_CONFIG, state)
        assert output() == ""

    def test_silent_mode_still_blocks(self, load_state, hosts_file):
        state = load_state(make_state())
        commands.cmd_start(make_args("start", silent_mode=True), DEFAULT_CONFIG, state)
        assert hosts_file.is_blocked

    def test_keeps_earlier_history(self, load_state, state_file):
        state = load_state(make_state(log=[session(7200, 3600)]))
        commands.cmd_start(make_args("start"), DEFAULT_CONFIG, state)
        assert len(state_file.read()["log"]) == 2

    def test_a_second_start_is_refused(self, load_state, hosts_file, output):
        state = load_state(make_state(running=True, log=[ongoing(600)]))
        commands.cmd_start(make_args("start"), DEFAULT_CONFIG, state)
        assert "already in progress" in output()
        assert not hosts_file.is_blocked
        assert not hosts_file.has_backup

    def test_a_second_start_does_not_touch_the_log(self, load_state, state_file):
        stored = make_state(running=True, log=[ongoing(600)])
        state = load_state(stored)
        commands.cmd_start(make_args("start"), DEFAULT_CONFIG, state)
        assert state_file.read() == stored

    def test_lock_option_locks_the_new_session(self, load_state, state_file):
        state = load_state(make_state())
        commands.cmd_start(make_args("start", locked_for="30m"), DEFAULT_CONFIG, state)
        stored = state_file.read()
        assert stored["lock"]["is_locked"] is True
        assert stored["lock"]["locked_for"] == 1800
        assert stored["lock"]["total_time_locked"] == 1800

    def test_without_the_lock_option_the_session_is_open(self, load_state, state_file):
        state = load_state(make_state())
        commands.cmd_start(make_args("start"), DEFAULT_CONFIG, state)
        assert state_file.read()["lock"]["is_locked"] is False

    def test_an_unparsable_lock_is_rejected_before_anything_is_blocked(
            self, load_state, state_file, hosts_file, output):
        state = load_state(make_state())
        commands.cmd_start(make_args("start", locked_for="banana"), DEFAULT_CONFIG, state)
        printed = output()
        assert "Error:" in printed
        assert "'banana' is not a valid lock time" in printed
        assert not hosts_file.is_blocked
        assert not hosts_file.has_backup
        assert state_file.read()["running"] is False

    def test_a_zero_lock_starts_an_immediately_stoppable_session(self, load_state, state_file):
        state = load_state(make_state())
        commands.cmd_start(make_args("start", locked_for="0"), DEFAULT_CONFIG, state)
        stored = state_file.read()
        assert stored["running"] is True
        assert stored["lock"]["is_locked"] is True
        assert State.from_dict(stored).is_unlock_allowed is True

    def test_works_on_a_machine_with_no_state_file_yet(self, load_state, state_file, hosts_file):
        assert not state_file.exists()
        commands.cmd_start(make_args("start"), DEFAULT_CONFIG, load_state())
        assert hosts_file.is_blocked
        assert state_file.read()["running"] is True


class TestCmdStop:

    def test_restores_the_original_hosts_file(self, load_state, blocked, original_hosts):
        state = load_state(make_state(running=True, log=[ongoing(600)]))
        commands.cmd_stop(make_args("stop"), None, state)
        assert blocked.read() == original_hosts
        assert not blocked.has_backup

    def test_closes_the_session_in_the_state_file(self, load_state, state_file, blocked):
        state = load_state(make_state(running=True, log=[ongoing(600)]))
        commands.cmd_stop(make_args("stop"), None, state)
        stored = state_file.read()
        assert stored["running"] is False
        assert stored["log"][-1][1] != "+"

    def test_announces_the_end(self, load_state, blocked, output):
        state = load_state(make_state(running=True, log=[ongoing(600)]))
        commands.cmd_stop(make_args("stop"), None, state)
        assert "Your self control session ended" in output()

    def test_silent_mode_says_nothing(self, load_state, blocked, output):
        state = load_state(make_state(running=True, log=[ongoing(600)]))
        commands.cmd_stop(make_args("stop", silent_mode=True), None, state)
        assert output() == ""

    def test_clears_the_lock(self, load_state, state_file, blocked):
        state = load_state(locked_state(locked_for=60, locked_since_seconds_ago=3600))
        commands.cmd_stop(make_args("stop"), None, state)
        stored = state_file.read()
        assert stored["lock"]["is_locked"] is False
        assert stored["lock"]["locked_since"] == 0

    def test_keeps_the_lifetime_lock_total(self, load_state, state_file, blocked):
        state = load_state(locked_state(locked_for=60, locked_since_seconds_ago=3600,
                                      total_time_locked=9000))
        commands.cmd_stop(make_args("stop"), None, state)
        assert state_file.read()["lock"]["total_time_locked"] == 9000

    def test_stopping_when_nothing_runs(self, load_state, output):
        state = load_state(make_state())
        commands.cmd_stop(make_args("stop"), None, state)
        assert "No self control session is currently running" in output()

    def test_stopping_when_nothing_runs_leaves_hosts_alone(self, load_state, blocked):
        state = load_state(make_state(running=False))
        commands.cmd_stop(make_args("stop"), None, state)
        assert blocked.is_blocked
        assert blocked.has_backup

    def test_a_live_lock_refuses_the_stop(self, load_state, state_file, blocked, output):
        state = load_state(locked_state(locked_for=3600))
        commands.cmd_stop(make_args("stop"), None, state)
        assert "This session is locked. You can not stop it." in output()
        assert blocked.is_blocked
        assert state_file.read()["running"] is True

    def test_an_expired_lock_allows_the_stop(self, load_state, state_file, blocked):
        state = load_state(locked_state(locked_for=60, locked_since_seconds_ago=3600))
        commands.cmd_stop(make_args("stop"), None, state)
        assert not blocked.is_blocked
        assert state_file.read()["running"] is False

    def test_a_backup_taken_while_blocked_keeps_the_session_alive(
            self, load_state, state_file, hosts_file, output):
        """Restoring such a backup 'succeeds' but leaves the sites blocked."""
        utils.forbid_sites(DEFAULT_CONFIG["forbidden_sites"])
        utils.backup_hosts()                      # backup already contains the rules
        state = load_state(make_state(running=True, log=[ongoing(600)]))

        commands.cmd_stop(make_args("stop"), None, state)

        printed = output()
        assert "ERROR:" in printed
        assert "still blocks the forbidden sites" in printed
        assert hosts_file.is_blocked
        stored = state_file.read()
        assert stored["running"] is True
        assert stored["log"][-1][1] == "+"

    def test_a_missing_backup_keeps_the_session_alive(self, load_state, state_file, output):
        utils.forbid_sites(DEFAULT_CONFIG["forbidden_sites"])   # blocked, no backup
        state = load_state(make_state(running=True, log=[ongoing(600)]))

        commands.cmd_stop(make_args("stop"), None, state)

        assert "still blocks the forbidden sites" in output()
        assert state_file.read()["running"] is True

    def test_hosts_cleaned_by_hand_still_ends_the_session(self, load_state, state_file):
        """No backup, but nothing is blocked either, so the session can end."""
        state = load_state(make_state(running=True, log=[ongoing(600)]))
        commands.cmd_stop(make_args("stop"), None, state)
        assert state_file.read()["running"] is False

    def test_start_then_stop_leaves_no_trace_in_hosts(self, load_state, hosts_file, original_hosts):
        state = load_state(make_state())
        commands.cmd_start(make_args("start"), DEFAULT_CONFIG, state)
        commands.cmd_stop(make_args("stop"), None, load_state())
        assert hosts_file.read() == original_hosts
        assert not hosts_file.has_backup


class TestCmdLock:

    def test_locks_a_running_session(self, load_state, state_file):
        state = load_state(make_state(running=True, log=[ongoing(600)]))
        commands.cmd_lock(make_args("lock", locked_for="45m"), None, state)
        stored = state_file.read()
        assert stored["lock"]["is_locked"] is True
        assert stored["lock"]["locked_for"] == 2700
        assert stored["lock"]["total_time_locked"] == 2700

    def test_adds_to_the_lifetime_total(self, load_state, state_file):
        state = load_state(make_state(running=True, log=[ongoing(600)], total_time_locked=3600))
        commands.cmd_lock(make_args("lock", locked_for="1h"), None, state)
        assert state_file.read()["lock"]["total_time_locked"] == 7200

    def test_needs_a_running_session(self, load_state, state_file, output):
        stored = make_state()
        state = load_state(stored)
        commands.cmd_lock(make_args("lock", locked_for="45m"), None, state)
        assert "No self control session is currently running" in output()
        assert state_file.read() == stored

    def test_a_live_lock_can_not_be_extended(self, load_state, state_file, output):
        stored = locked_state(locked_for=3600)
        state = load_state(stored)
        commands.cmd_lock(make_args("lock", locked_for="2h"), None, state)
        assert "This session is already locked" in output()
        assert state_file.read() == stored

    def test_an_expired_lock_can_be_renewed(self, load_state, state_file):
        state = load_state(locked_state(locked_for=60, locked_since_seconds_ago=3600,
                                      total_time_locked=60))
        commands.cmd_lock(make_args("lock", locked_for="2h"), None, state)
        stored = state_file.read()
        assert stored["lock"]["locked_for"] == 7200
        assert stored["lock"]["total_time_locked"] == 7260

    def test_an_unparsable_time_changes_nothing(self, load_state, state_file, output):
        stored = make_state(running=True, log=[ongoing(600)])
        state = load_state(stored)
        commands.cmd_lock(make_args("lock", locked_for="soon"), None, state)
        assert "'soon' is not a valid lock time" in output()
        assert state_file.read() == stored

    def test_the_lock_is_visible_to_a_following_stop(self, load_state, blocked, output):
        state = load_state(make_state(running=True, log=[ongoing(600)]))
        commands.cmd_lock(make_args("lock", locked_for="1h"), None, state)
        commands.cmd_stop(make_args("stop"), None, load_state())
        assert "This session is locked. You can not stop it." in output()


class TestCmdStatus:

    @pytest.fixture(autouse=True)
    def spy_on_progressbar(self, monkeypatch):
        calls = []
        monkeypatch.setattr(lock, "static_progressbar", lambda state: calls.append(state))
        return calls

    def test_idle(self, load_state, output):
        state = load_state(make_state())
        commands.cmd_status(make_args("status"), None, state)
        assert output() == "Self control session is not activated"

    def test_running(self, load_state, output):
        state = load_state(make_state(running=True, log=[ongoing(3600)]))
        commands.cmd_status(make_args("status"), None, state)
        printed = output()
        assert "Self control session is activated" in printed
        assert "Current session: 1 hour" in printed

    def test_a_live_lock_draws_the_progress_bar(self, load_state, spy_on_progressbar):
        state = load_state(locked_state(locked_for=3600))
        commands.cmd_status(make_args("status"), None, state)
        assert len(spy_on_progressbar) == 1

    def test_no_progress_bar_without_a_lock(self, load_state, spy_on_progressbar):
        state = load_state(make_state(running=True, log=[ongoing(600)]))
        commands.cmd_status(make_args("status"), None, state)
        assert spy_on_progressbar == []

    def test_no_progress_bar_for_an_expired_lock(self, load_state, spy_on_progressbar):
        state = load_state(locked_state(locked_for=60, locked_since_seconds_ago=3600))
        commands.cmd_status(make_args("status"), None, state)
        assert spy_on_progressbar == []

    def test_no_progress_bar_when_idle(self, load_state, spy_on_progressbar):
        state = load_state(make_state())
        commands.cmd_status(make_args("status"), None, state)
        assert spy_on_progressbar == []


class TestCmdStats:

    def test_prints_status_totals_and_achievements(self, load_state, output):
        state = load_state(make_state(log=[session(7200, 3600)]))
        commands.cmd_stats(make_args("stats"), DEFAULT_CONFIG, state)
        printed = output()
        assert "Self control session is not activated" in printed
        assert "Total time: 1 hour" in printed
        assert "Total sessions: 1" in printed
        for badge in ("Stoic", "Marathonist", "Ascetic", "Totalitarian"):
            assert badge in printed

    def test_works_on_a_fresh_install(self, load_state, state_file, output):
        assert not state_file.exists()
        commands.cmd_stats(make_args("stats"), DEFAULT_CONFIG, load_state())
        assert "Total sessions: 0" in output()


class TestCmdConfig:

    @pytest.fixture
    def editor_calls(self, monkeypatch):
        calls = []
        monkeypatch.setattr(commands, "call", lambda argv: calls.append(argv) or 0)
        return calls

    def test_opens_the_config_in_the_editor(self, monkeypatch, editor_calls):
        monkeypatch.setenv("EDITOR", "nano")
        commands.cmd_config(make_args("config", config_path="/etc/stopro/conf.yml"), None, None)
        assert editor_calls == [["nano", "/etc/stopro/conf.yml"]]

    def test_editor_arguments_are_preserved(self, monkeypatch, editor_calls):
        monkeypatch.setenv("EDITOR", "code --wait")
        commands.cmd_config(make_args("config", config_path="/tmp/conf.yml"), None, None)
        assert editor_calls == [["code", "--wait", "/tmp/conf.yml"]]

    def test_falls_back_to_vim(self, monkeypatch, editor_calls):
        monkeypatch.delenv("EDITOR", raising=False)
        commands.cmd_config(make_args("config"), None, None)
        assert editor_calls == [["/usr/bin/vim", "/etc/stopro/conf.yml"]]

    def test_an_empty_editor_variable_falls_back_to_vim(self, monkeypatch, editor_calls):
        monkeypatch.setenv("EDITOR", "")
        commands.cmd_config(make_args("config"), None, None)
        assert editor_calls == [["/usr/bin/vim", "/etc/stopro/conf.yml"]]

    def test_honours_a_custom_config_path(self, monkeypatch, editor_calls):
        monkeypatch.setenv("EDITOR", "nano")
        commands.cmd_config(make_args("config", config_path="/home/user/stopro.yml"), None, None)
        assert editor_calls[0][-1] == "/home/user/stopro.yml"

    def test_a_missing_editor_is_reported(self, monkeypatch, output):
        monkeypatch.setenv("EDITOR", "no-such-editor")

        def explode(_argv):
            raise OSError("No such file or directory")
        monkeypatch.setattr(commands, "call", explode)

        with pytest.raises(SystemExit) as exit_info:
            commands.cmd_config(make_args("config"), None, None)
        assert exit_info.value.code == 1
        assert "Could not start editor" in output()


class TestCmdClearHistory:

    @pytest.fixture
    def answer(self, monkeypatch):
        def _answer(text):
            monkeypatch.setattr("builtins.input", lambda: text)
        return _answer

    def test_confirmed_wipe_resets_the_state(self, load_state, state_file, answer, output):
        state = load_state(make_state(log=[session(7200, 3600)], total_time_locked=900))
        answer("y")
        commands.cmd_clear_history(make_args("clear-history"), None, state)
        stored = state_file.read()
        assert stored["log"] == []
        assert stored["lock"]["total_time_locked"] == 0
        assert "History was successfully deleted" in output()

    @pytest.mark.parametrize("reply", ["y", "Y", "yes", "YES", "Yes"])
    def test_every_form_of_yes_is_accepted(self, load_state, state_file, answer, reply):
        state = load_state(make_state(log=[session(7200, 3600)]))
        answer(reply)
        commands.cmd_clear_history(make_args("clear-history"), None, state)
        assert state_file.read()["log"] == []

    @pytest.mark.parametrize("reply", ["n", "N", "no", "", "later", "ye"])
    def test_anything_else_keeps_the_history(self, load_state, state_file, answer, reply, output):
        stored = make_state(log=[session(7200, 3600)])
        state = load_state(stored)
        answer(reply)
        commands.cmd_clear_history(make_args("clear-history"), None, state)
        assert state_file.read() == stored
        assert "History was successfully deleted" not in output()

    def test_warns_before_asking(self, load_state, answer, output):
        state = load_state(make_state())
        answer("n")
        commands.cmd_clear_history(make_args("clear-history"), None, state)
        printed = output()
        assert "Are you sure" in printed
        assert "this is permanent" in printed

    def test_refused_during_a_session(self, load_state, state_file, answer, output):
        stored = make_state(running=True, log=[ongoing(600)])
        state = load_state(stored)
        answer("y")
        commands.cmd_clear_history(make_args("clear-history"), None, state)
        assert "You can not clear history during self control session" in output()
        assert state_file.read() == stored

    def test_does_not_prompt_during_a_session(self, load_state, monkeypatch):
        def explode():
            raise AssertionError("must not ask while a session is running")
        monkeypatch.setattr("builtins.input", explode)
        state = load_state(make_state(running=True, log=[ongoing(600)]))
        commands.cmd_clear_history(make_args("clear-history"), None, state)


class TestKnownGaps:

    @pytest.mark.xfail(reason="an empty conf.yml makes load_yaml return None and "
                              "cmd_start dies with a TypeError instead of an error message",
                       raises=TypeError, strict=True)
    def test_start_with_an_empty_config_reports_a_readable_error(self, load_state, output):
        state = load_state(make_state())
        commands.cmd_start(make_args("start"), None, state)
        assert "ERROR:" in output()
