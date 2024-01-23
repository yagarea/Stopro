from utils import get_state, write_yaml, STATE_PATH, format_second
from dateutil import parser
from datetime import datetime, timedelta
from rich.progress import Progress, BarColumn, TimeRemainingColumn
from time import sleep


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


def is_unlock_allowed(state):
    if not is_locked():
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
        if raw_time.endswith("s"):
            return int(raw_time[:-1])
        elif raw_time.endswith("m"):
            return int(raw_time[:-1]) * 60
        elif raw_time.endswith("h"):
            return int(raw_time[:-1]) * 60 * 60
        elif raw_time.endswith("d"):
            return int(raw_time[:-1]) * 60 * 60 * 24
        else:
            return int(raw_time)


def get_remaining_time(state):
    can_be_open_after = parser.parse(state["lock"]["locked_since"]) + timedelta(seconds=state["lock"]["locked_for"])
    return  (can_be_open_after - datetime.now()).total_seconds()


