"""Small builders shared by the test modules.

Kept free of fixtures so they can be used inside parametrize lists too.
"""

from argparse import Namespace
from datetime import datetime, timedelta


DEFAULT_CONFIG = {"forbidden_sites": ["example.com", "example.org", "example.net"]}


def ago(**delta) -> str:
    """An ISO timestamp `delta` in the past, the format lock.lock() writes."""
    return (datetime.now() - timedelta(**delta)).isoformat()


def ongoing(start_seconds_ago: float) -> list:
    """A log entry for a session that is still open."""
    return [ago(seconds=start_seconds_ago), "+"]


def session(start_seconds_ago: float, end_seconds_ago: float) -> list:
    """A log entry for a finished session."""
    return [ago(seconds=start_seconds_ago), ago(seconds=end_seconds_ago)]


def make_state(*, running=False, log=None, is_locked=False, locked_since=0,
               locked_for=0, total_time_locked=0) -> dict:
    """A state dictionary shaped exactly like create_new_clean_state() writes."""
    return {
        "running": running,
        "log": [] if log is None else log,
        "lock": {
            "is_locked": is_locked,
            "locked_since": locked_since,
            "locked_for": locked_for,
            "total_time_locked": total_time_locked,
        },
    }


def locked_state(*, locked_for=1800, locked_since_seconds_ago=0, **overrides) -> dict:
    """A running session locked `locked_for` seconds, started in the past."""
    overrides.setdefault("log", [ongoing(locked_since_seconds_ago + 60)])
    return make_state(
        running=True,
        is_locked=True,
        locked_since=ago(seconds=locked_since_seconds_ago),
        locked_for=locked_for,
        **overrides,
    )


def make_args(command="status", **overrides) -> Namespace:
    """The argparse namespace the cmd_* functions expect."""
    values = {
        "command": command,
        "debug": False,
        "silent_mode": False,
        "locked_for": "",
        "config_path": "/etc/stopro/conf.yml",
    }
    values.update(overrides)
    return Namespace(**values)
