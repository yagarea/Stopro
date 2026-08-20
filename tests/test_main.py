"""Tests for stopro.__main__: the root check and the command dispatch."""

import importlib.metadata

import pytest

from helpers import DEFAULT_CONFIG, make_args
from stopro import __main__ as entrypoint


# command -> (handler, needs root, reads the config file)
DISPATCH = [
    ("start", "cmd_start", True, True),
    ("stop", "cmd_stop", True, False),
    ("lock", "cmd_lock", False, False),
    ("config", "cmd_config", True, False),
    ("status", "cmd_status", False, False),
    ("stats", "cmd_stats", False, True),
    ("clear-history", "cmd_clear_history", False, False),
]

HANDLERS = [handler for _, handler, _, _ in DISPATCH]
ROOT_COMMANDS = [(command, handler) for command, handler, root, _ in DISPATCH if root]
USER_COMMANDS = [(command, handler) for command, handler, root, _ in DISPATCH if not root]


@pytest.fixture
def run(monkeypatch):
    """Drive main() with every side effect recorded instead of performed."""
    class _Run:
        def __init__(self):
            self.calls = {}
            self.loaded_configs = []
            self.euid_checks = 0

        def __call__(self, command, *, euid=0, **argument_overrides):
            arguments = make_args(command, **argument_overrides)
            monkeypatch.setattr(entrypoint, "get_args", lambda: arguments)

            def geteuid():
                self.euid_checks += 1
                return euid
            monkeypatch.setattr(entrypoint, "geteuid", geteuid)

            def load_yaml(path, debug=False):
                self.loaded_configs.append(path)
                return DEFAULT_CONFIG
            monkeypatch.setattr(entrypoint, "load_yaml", load_yaml)

            for handler in HANDLERS:
                monkeypatch.setattr(
                    entrypoint, handler,
                    lambda arguments, config, handler=handler:
                        self.calls.setdefault(handler, []).append((arguments, config)))

            entrypoint.main()
            return arguments
    return _Run()


class TestDispatch:

    @pytest.mark.parametrize("command, handler, _root, _config", DISPATCH)
    def test_each_command_reaches_its_handler(self, run, command, handler, _root, _config):
        run(command)
        assert list(run.calls) == [handler]
        assert len(run.calls[handler]) == 1

    @pytest.mark.parametrize("command, handler, _root, _config", DISPATCH)
    def test_the_handler_receives_the_parsed_arguments(self, run, command, handler, _root, _config):
        arguments = run(command)
        assert run.calls[handler][0][0] is arguments

    def test_an_unknown_command_does_nothing(self, run):
        run("nonsense")
        assert run.calls == {}


class TestConfigLoading:

    @pytest.mark.parametrize("command, _handler, _root, reads_config", DISPATCH)
    def test_only_start_and_stats_read_the_config(self, run, command, _handler, _root, reads_config):
        run(command)
        assert bool(run.loaded_configs) is reads_config

    def test_the_config_path_from_the_command_line_is_used(self, run):
        run("start", config_path="/home/user/stopro.yml")
        assert run.loaded_configs == ["/home/user/stopro.yml"]

    @pytest.mark.parametrize("command, handler, _root, reads_config", DISPATCH)
    def test_the_handler_gets_the_config_only_when_it_was_read(
            self, run, command, handler, _root, reads_config):
        run(command)
        _, config = run.calls[handler][0]
        assert config == (DEFAULT_CONFIG if reads_config else None)

    def test_version_never_touches_the_config(self, run, monkeypatch):
        monkeypatch.setattr(importlib.metadata, "version", lambda name: "0.0.1")
        run("version")
        assert run.loaded_configs == []


class TestRootCheck:

    @pytest.mark.parametrize("command, _handler, needs_root, _config", DISPATCH)
    def test_only_the_commands_touching_etc_check_for_root(
            self, run, command, _handler, needs_root, _config):
        run(command)
        assert (run.euid_checks > 0) is needs_root

    @pytest.mark.parametrize("command, handler", ROOT_COMMANDS)
    def test_a_normal_user_is_turned_away(self, run, command, handler, output):
        with pytest.raises(SystemExit) as exit_info:
            run(command, euid=1000)
        assert exit_info.value.code == 1
        assert "You need root permission" in output()
        assert run.calls == {}

    @pytest.mark.parametrize("command, _handler", USER_COMMANDS)
    def test_a_normal_user_may_run_the_read_only_commands(self, run, command, _handler):
        run(command, euid=1000)
        assert run.calls != {}

    def test_check_root_passes_for_uid_zero(self, monkeypatch):
        monkeypatch.setattr(entrypoint, "geteuid", lambda: 0)
        entrypoint.check_root()

    def test_check_root_stops_everyone_else(self, monkeypatch, output):
        monkeypatch.setattr(entrypoint, "geteuid", lambda: 1000)
        with pytest.raises(SystemExit) as exit_info:
            entrypoint.check_root()
        assert exit_info.value.code == 1
        assert "You need root permission" in output()


class TestVersion:

    def test_prints_the_installed_version(self, run, monkeypatch, output):
        monkeypatch.setattr(importlib.metadata, "version", lambda name: "1.2.3")
        run("version")
        assert output() == "1.2.3"

    def test_asks_for_the_stopro_distribution(self, run, monkeypatch):
        asked = []
        monkeypatch.setattr(importlib.metadata, "version", asked.append)
        run("version")
        assert asked == ["stopro"]

    def test_needs_no_root(self, run, monkeypatch):
        monkeypatch.setattr(importlib.metadata, "version", lambda name: "1.2.3")
        run("version", euid=1000)
        assert run.euid_checks == 0

    def test_reports_the_real_installed_version(self, run, output):
        run("version")
        assert output() == importlib.metadata.version("stopro")
