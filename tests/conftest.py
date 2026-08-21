"""Fixtures that keep the suite away from the real /usr/share/stopro and /etc.

Stopro addresses the filesystem through module level constants and caches the
state with functools.cache, so every test needs both rebound to a tmp_path and
the cache cleared.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
import yaml

from stopro import __main__ as entrypoint
from stopro import achievments, commands, lock, stats, utils
from stopro import state as state_module
from stopro.state import State


ORIGINAL_HOSTS = "127.0.0.1\tlocalhost\n::1\t\tip6-localhost\n"

# commands.py does `from .utils import *`, so it holds its own binding of every
# constant; rebinding only utils would leave stale copies behind.
_MODULES = (utils, commands, lock, stats, achievments, entrypoint, state_module)


def _rebind(monkeypatch, name, value):
    for module in _MODULES:
        if hasattr(module, name):
            monkeypatch.setattr(module, name, value)


@pytest.fixture(autouse=True)
def paths(tmp_path, monkeypatch):
    """Point every path constant at a tmp_path of this test's own."""
    state_path = tmp_path / "share" / "stopro" / "state.yml"
    hosts_path = tmp_path / "etc" / "hosts"
    backup_path = tmp_path / "etc" / "hosts.stopro_backup"
    hosts_path.parent.mkdir(parents=True)
    hosts_path.write_text(ORIGINAL_HOSTS)

    _rebind(monkeypatch, "STATE_PATH", str(state_path))
    _rebind(monkeypatch, "HOSTS_PATH", str(hosts_path))
    _rebind(monkeypatch, "HOSTS_BACKUP_PATH", str(backup_path))

    # rich wraps at the terminal width; pin it so assertions on printed text do
    # not depend on the terminal the suite happens to run in.
    monkeypatch.setenv("COLUMNS", "200")

    yield SimpleNamespace(state=state_path, hosts=hosts_path, backup=backup_path)


class _StateFile:
    def __init__(self, path):
        self.path = path

    def write(self, state):
        """Persist a state dict in the on-disk format."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(yaml.dump(state))
        return state

    def read(self):
        return yaml.safe_load(self.path.read_text())

    def exists(self):
        return self.path.exists()


class _HostsFile:
    def __init__(self, hosts, backup):
        self.path = hosts
        self.backup_path = backup

    def read(self):
        return self.path.read_text()

    def write(self, content):
        self.path.write_text(content)

    def write_backup(self, content):
        self.backup_path.write_text(content)

    @property
    def is_blocked(self):
        return utils.BLOCK_MARKER in self.path.read_text()

    @property
    def has_backup(self):
        return self.backup_path.exists()


@pytest.fixture
def state_file(paths):
    return _StateFile(paths.state)


@pytest.fixture
def load_state(state_file):
    """Seed the state file and load it the way main() does."""
    def _load(state_dict=None):
        if state_dict is not None:
            state_file.write(state_dict)
        return State.load()
    return _load


@pytest.fixture
def hosts_file(paths):
    return _HostsFile(paths.hosts, paths.backup)


@pytest.fixture
def original_hosts():
    return ORIGINAL_HOSTS


@pytest.fixture
def output(capsys):
    """Read captured stdout with whitespace collapsed.

    rich decides on its own where to break lines, so comparing on a single
    normalised line keeps assertions about wording independent of layout.
    """
    def _read():
        return " ".join(capsys.readouterr().out.split())
    return _read


@pytest.fixture
def freeze_now(monkeypatch):
    """Pin datetime.now() inside the given modules to a fixed moment."""
    def _freeze(moment, *modules):
        class _Frozen(datetime):
            @classmethod
            def now(cls, tz=None):
                return moment
        for module in modules:
            monkeypatch.setattr(module, "datetime", _Frozen)
        return moment
    return _freeze


@pytest.fixture
def advancing_now(monkeypatch):
    """Make datetime.now() step forward by `step` on every call.

    Lets the blocking progress bar be driven to completion without sleeping.
    """
    def _advance(start, *modules, step=timedelta(seconds=1)):
        ticks = iter(range(10_000))

        class _Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return start + step * next(ticks)
        for module in modules:
            monkeypatch.setattr(module, "datetime", _Clock)
        return _Clock
    return _advance
