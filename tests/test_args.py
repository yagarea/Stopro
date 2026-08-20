"""Tests for stopro.args: the command line surface described in the README."""

import sys

import pytest

from stopro.args import get_args


@pytest.fixture
def parse(monkeypatch):
    def _parse(*argv):
        monkeypatch.setattr(sys, "argv", ["stopro", *argv])
        return get_args()
    return _parse


class TestCommands:

    @pytest.mark.parametrize("command", [
        "start", "stop", "lock", "status", "config", "stats", "clear-history", "version",
    ])
    def test_every_documented_command_parses(self, parse, command):
        argv = [command, "30m"] if command == "lock" else [command]
        assert parse(*argv).command == command

    def test_a_command_is_required(self, parse):
        with pytest.raises(SystemExit) as exit_info:
            parse()
        assert exit_info.value.code == 2

    def test_unknown_commands_are_rejected(self, parse):
        with pytest.raises(SystemExit) as exit_info:
            parse("procrastinate")
        assert exit_info.value.code == 2

    def test_help_exits_cleanly(self, parse):
        with pytest.raises(SystemExit) as exit_info:
            parse("--help")
        assert exit_info.value.code == 0


class TestGlobalOptions:

    def test_config_path_defaults_to_etc(self, parse):
        assert parse("status").config_path == "/etc/stopro/conf.yml"

    @pytest.mark.parametrize("flag", ["-c", "--config"])
    def test_config_path_can_be_overridden(self, parse, flag):
        assert parse(flag, "/home/user/stopro.yml", "status").config_path == "/home/user/stopro.yml"

    def test_debug_is_off_by_default(self, parse):
        assert parse("status").debug is False

    @pytest.mark.parametrize("flag", ["-d", "--debug"])
    def test_debug_can_be_switched_on(self, parse, flag):
        assert parse(flag, "status").debug is True

    def test_silent_is_off_by_default(self, parse):
        assert parse("status").silent_mode is False

    @pytest.mark.parametrize("flag", ["-s", "--silent"])
    def test_silent_can_be_switched_on_before_the_command(self, parse, flag):
        assert parse(flag, "start").silent_mode is True

    def test_global_options_combine(self, parse):
        arguments = parse("-d", "-s", "-c", "/tmp/c.yml", "start")
        assert (arguments.debug, arguments.silent_mode, arguments.config_path) == \
               (True, True, "/tmp/c.yml")


class TestStart:

    def test_defaults(self, parse):
        arguments = parse("start")
        assert arguments.locked_for == ""
        assert arguments.silent_mode is False

    @pytest.mark.parametrize("flag", ["-l", "--lock"])
    def test_lock_option(self, parse, flag):
        assert parse("start", flag, "30m").locked_for == "30m"

    @pytest.mark.parametrize("flag", ["-s", "--silent"])
    def test_silent_after_the_command(self, parse, flag):
        assert parse("start", flag).silent_mode is True

    def test_lock_and_silent_together(self, parse):
        arguments = parse("start", "-s", "-l", "1d")
        assert (arguments.silent_mode, arguments.locked_for) == (True, "1d")

    def test_the_lock_value_is_not_validated_here(self, parse):
        """Validation belongs to lock.parse_lock_time, which reports it nicely."""
        assert parse("start", "-l", "banana").locked_for == "banana"


class TestStop:

    def test_defaults(self, parse):
        assert parse("stop").silent_mode is False

    @pytest.mark.parametrize("flag", ["-s", "--silent"])
    def test_silent_after_the_command(self, parse, flag):
        assert parse("stop", flag).silent_mode is True

    def test_takes_no_lock_option(self, parse):
        with pytest.raises(SystemExit):
            parse("stop", "-l", "30m")


class TestLock:

    def test_takes_the_duration_as_a_positional(self, parse):
        assert parse("lock", "3h").locked_for == "3h"

    def test_the_duration_is_required(self, parse):
        with pytest.raises(SystemExit) as exit_info:
            parse("lock")
        assert exit_info.value.code == 2

    def test_the_value_is_kept_as_text(self, parse):
        assert parse("lock", "30").locked_for == "30"


class TestCommandsWithoutOptions:

    @pytest.mark.parametrize("command", ["status", "config", "stats", "clear-history", "version"])
    def test_they_carry_no_lock_argument(self, parse, command):
        assert not hasattr(parse(command), "locked_for")

    @pytest.mark.parametrize("command", ["status", "config", "stats", "clear-history", "version"])
    def test_they_still_get_the_global_options(self, parse, command):
        arguments = parse(command)
        assert arguments.silent_mode is False
        assert arguments.debug is False
        assert arguments.config_path == "/etc/stopro/conf.yml"
