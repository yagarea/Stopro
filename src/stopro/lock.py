from .utils import get_state, write_yaml, STATE_PATH, format_second
from dateutil import parser
from datetime import datetime, timedelta
from rich.progress import Progress, BarColumn, TimeRemainingColumn
from rich import print
from time import sleep


UNIT_MULTIPLIERS = {
    "s": 1,
    "m": 60,
    "h": 60 * 60,
    "d": 60 * 60 * 24,
}


class InvalidLockTime(Exception):
    """Raised when a lock time string can not be parsed."""

    def __init__(self, value):
        self.value = value
        super().__init__(
            f"'{value}' is not a valid lock time.\n"
            "Use a whole number optionally followed by a unit: "
            "s (seconds), m (minutes), h (hours) or d (days).\n"
            "For example: 30s, 5m, 2h or 1d."
        )


def lock(state, for_how_long):
    state["lock"]["is_locked"] = True
    state["lock"]["locked_since"] = datetime.now().isoformat()
    state["lock"]["locked_for"] = for_how_long
    state["lock"]["total_time_locked"] += for_how_long
    return state


def unlock(state):
    state["lock"]["is_locked"] = False
    state["lock"]["locked_since"] = 0
    state["lock"]["locked_for"] = 0
    return state


def is_locked():
    return get_state()["lock"]["is_locked"]


def is_unlock_allowed(state, debug=False):
    if debug:
        print(f"DEBUG:\tLocked since: {state['lock']['locked_since']}")
        print(f"DEBUG:\tLocked for: {state['lock']['locked_for']}")
        print(f"DEBUG:\tTotal time locked: {state['lock']['total_time_locked']}")
        print(f"DEBUG:\tIs locked: {state['lock']['is_locked']}")
    if not state["lock"]["is_locked"]:
        return True
    can_be_open_after = parser.parse(state["lock"]["locked_since"]) + timedelta(seconds=state["lock"]["locked_for"])
    return datetime.now() > can_be_open_after


def progressbar(state):
    locked_since = parser.parse(state["lock"]["locked_since"])
    locked_for = state["lock"]["locked_for"]
    progress = Progress("Lock:", "[progress.percentage]{task.percentage:>3.0f}%", BarColumn(), TimeRemainingColumn())
    task = progress.add_task("Locking...", total=locked_for)
    progress.update(task, advance=(int(state["lock"]["locked_for"]) - get_remaining_time(state)))
    progress.start()
    while not is_unlock_allowed(state):
        progress.update(task, advance=1)
        sleep(1)
    progress.stop()


def static_progressbar(state):
    locked_since = parser.parse(state["lock"]["locked_since"])
    locked_for = state["lock"]["locked_for"]
    progress = Progress("Lock:", "[progress.percentage]{task.percentage:>3.0f}%", BarColumn(), f"{format_second(get_remaining_time(state))} remaining")
    task = progress.add_task("Locking...", total=locked_for)
    progress.update(task, advance=(locked_for - get_remaining_time(state)))
    progress.start()
    progress.update(task, advance=0)
    progress.stop()


def parse_lock_time(raw_time):
    value = raw_time.strip()
    multiplier = 1
    if value and value[-1] in UNIT_MULTIPLIERS:
        multiplier = UNIT_MULTIPLIERS[value[-1]]
        value = value[:-1]
    try:
        seconds = int(value)
    except ValueError:
        raise InvalidLockTime(raw_time)
    if seconds < 0:
        raise InvalidLockTime(raw_time)
    return seconds * multiplier


def get_remaining_time(state):
    can_be_open_after = parser.parse(state["lock"]["locked_since"]) + timedelta(seconds=state["lock"]["locked_for"])
    return  (can_be_open_after - datetime.now()).total_seconds()


