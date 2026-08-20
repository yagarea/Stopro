"""Tests for stopro.state.State.

State is still unfinished, so these are marked xfail: they describe what the
class is evidently meant to do and will start passing (as XPASS) once it does.
Two things stand in the way today:

  * load_yaml is used but never imported, so every construction raises NameError
  * it reads state_dict["is_running"], while create_new_clean_state() and
    log_activity() write that flag under the key "running"
"""

import pytest

from helpers import make_state, ongoing
from stopro.state import State


pytestmark = pytest.mark.xfail(
    reason="stopro.state.State is unfinished: load_yaml is not imported and the "
           "'is_running' key does not match the 'running' key in the state file",
    raises=(NameError, KeyError),
    strict=True,
)


def test_reads_a_state_file_written_by_the_rest_of_the_app(state_file):
    stored = state_file.write(make_state(running=True, log=[ongoing(600)],
                                         is_locked=True, locked_since="2024-05-01T09:00:00",
                                         locked_for=1800, total_time_locked=5400))
    state = State(str(state_file.path))
    assert state.log == stored["log"]
    assert state.is_running is True
    assert state.is_locked is True
    assert state.locked_since == "2024-05-01T09:00:00"
    assert state.total_time_locked == 5400


def test_reads_a_freshly_created_state(state_file, paths):
    from stopro import utils
    utils.create_new_clean_state()
    state = State(str(paths.state))
    assert state.log == []
    assert state.is_running is False
    assert state.is_locked is False
    assert state.total_time_locked == 0
