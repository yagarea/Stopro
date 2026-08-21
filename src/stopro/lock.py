from .utils import format_second
from rich.progress import Progress, BarColumn, TimeRemainingColumn
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


def progressbar(state):
    locked_for = state.locked_for
    progress = Progress("Lock:", "[progress.percentage]{task.percentage:>3.0f}%", BarColumn(), TimeRemainingColumn())
    task = progress.add_task("Locking...", total=locked_for)
    progress.update(task, advance=(int(locked_for) - state.remaining_lock_time))
    progress.start()
    while not state.is_unlock_allowed:
        progress.update(task, advance=1)
        sleep(1)
    progress.stop()


def static_progressbar(state):
    locked_for = state.locked_for
    progress = Progress("Lock:", "[progress.percentage]{task.percentage:>3.0f}%", BarColumn(), f"{format_second(state.remaining_lock_time)} remaining")
    task = progress.add_task("Locking...", total=locked_for)
    progress.update(task, advance=(locked_for - state.remaining_lock_time))
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
