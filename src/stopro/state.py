"""The stopro state and everything that changes it.

The state file format predates this class and is unchanged: a YAML mapping with
"log", "running" and a "lock" section. Attribute names do not have to match the
file keys (is_running is stored as "running"); from_dict() and as_dict() are the
only two places that know about the mapping.

Every method that changes the state also saves it, so a command can not leave
the file behind out of date.
"""

from datetime import datetime, timedelta
from os.path import isfile

from dateutil import parser

from . import utils


class State:

    def __init__(self, state_file=None, *, log=None, is_running=False,
                 is_locked=False, locked_since=0, locked_for=0, total_time_locked=0):
        self.path = state_file or utils.STATE_PATH
        self.log = [] if log is None else log
        self.is_running = is_running
        self.is_locked = is_locked
        self.locked_since = locked_since
        self.locked_for = locked_for
        self.total_time_locked = total_time_locked

    def __repr__(self):
        return (f"State(path={self.path!r}, is_running={self.is_running}, "
                f"sessions={len(self.log)}, is_locked={self.is_locked}, "
                f"locked_since={self.locked_since!r}, locked_for={self.locked_for}, "
                f"total_time_locked={self.total_time_locked})")

    # Loading and saving ----------------------------------------------------

    @classmethod
    def load(cls, state_file=None, debug=False):
        """Read the state file, creating a clean one when it does not exist."""
        state_file = state_file or utils.STATE_PATH
        if not isfile(state_file):
            state = cls(state_file)
            state.save()
            return state
        state = cls.from_dict(utils.load_yaml(state_file, debug), state_file)
        if debug:
            print(f"DEBUG:\t{state!r}")
        return state

    @classmethod
    def from_dict(cls, state_dict, state_file=None):
        lock_state = state_dict["lock"]
        return cls(state_file,
                   log=state_dict["log"],
                   is_running=state_dict["running"],
                   is_locked=lock_state["is_locked"],
                   locked_since=lock_state["locked_since"],
                   locked_for=lock_state["locked_for"],
                   total_time_locked=lock_state["total_time_locked"])

    def as_dict(self):
        return {
            "log": self.log,
            "running": self.is_running,
            "lock": {
                "is_locked": self.is_locked,
                "locked_for": self.locked_for,
                "locked_since": self.locked_since,
                "total_time_locked": self.total_time_locked,
            },
        }

    def save(self):
        utils.create_state_directory(self.path)
        utils.write_yaml(self.as_dict(), self.path)

    # The session -----------------------------------------------------------

    def start(self, locked_for=None):
        """Open a session, locked for `locked_for` seconds when given."""
        self.log.append([str(datetime.now()), "+"])
        self.is_running = True
        if locked_for is not None:
            self._lock(locked_for)
        self.save()

    def stop(self):
        """Close the running session and release its lock."""
        if len(self.log) > 0:
            self.log[-1][1] = str(datetime.now())
        else:
            print("log corrupted")
            self.log.append(["?", str(datetime.now())])
        self.is_running = False
        self._unlock()
        self.save()

    def clear(self):
        """Forget all history and start over from a clean state."""
        self.log = []
        self.is_running = False
        self.total_time_locked = 0
        self._unlock()
        self.save()

    # The lock --------------------------------------------------------------

    def lock(self, seconds):
        """Lock the session for `seconds` from now."""
        self._lock(seconds)
        self.save()

    def unlock(self):
        """Release the lock without touching the session itself."""
        self._unlock()
        self.save()

    @property
    def is_unlock_allowed(self):
        """Whether the session may be stopped right now."""
        if not self.is_locked:
            return True
        return datetime.now() > self.locked_until

    @property
    def remaining_lock_time(self):
        """Seconds left on the lock, negative once it has run out."""
        return (self.locked_until - datetime.now()).total_seconds()

    @property
    def locked_until(self):
        return parser.parse(self.locked_since) + timedelta(seconds=self.locked_for)

    def _lock(self, seconds):
        self.is_locked = True
        self.locked_since = datetime.now().isoformat()
        self.locked_for = seconds
        self.total_time_locked += seconds

    def _unlock(self):
        self.is_locked = False
        self.locked_since = 0
        self.locked_for = 0
