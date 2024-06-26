from dateutil import parser
from datetime import timedelta, datetime
from rich import print
import lock
from utils import format_second


# Get list of durations of all sessions
def get_session_durations(sessions: list) -> [float]:
    output = list()
    for session in sessions:
        if session[1] != "+":
            start, end = parser.parse(session[0]), parser.parse(session[1])
            output.append((end - start))
    return output


# Prints the status of the current session
def print_session_status(state):
    if state["running"]:
        print("Self control session is [bold green]activated[/bold green]")
        print(f"[bold]Current session:[/bold]\t{format_second(get_duration_of_ongoing_session(state['log']))}")
        print_lock_status(state)
    else:
        print("Self control session is [bold red]not activated[/bold red]")


# Get the longest session
def get_longest_session(sessions: list):
    if len(sessions) == 0:
        return 0
    elif len(sessions) == 1:
        return get_duration_of_ongoing_session(sessions)
    return max(max([i.total_seconds() for i in get_session_durations(sessions)]), get_duration_of_ongoing_session(sessions))


# Prints the global stats
def print_global_stats(state):
    total_time = get_total_time(state)
    session_count = (len(state["log"]) - (1 if state["running"] else 0))
    if session_count == 0:
        avg_time = get_duration_of_ongoing_session(state["log"]) if state["running"] else 0
    else:
        avg_time = total_time / session_count
    longest_session = get_longest_session(state["log"])

    print("")
    print(f"[bold]Total time:[/bold]\t{format_second(total_time)}")
    print(f"[bold]Average time:[/bold]\t{format_second(avg_time)}")
    print(f"[bold]Total sessions:[/bold]\t{session_count}")
    print(f"[bold]Longest:[/bold]\t{format_second(longest_session)}")


# Get the duration of the ongoing session in seconds
def get_duration_of_ongoing_session(log):
    current_session_start = log[-1][0]
    return (datetime.now() - parser.parse(current_session_start)).total_seconds()


# Get the total time of all sessions in seconds
def get_total_time(state):
    return sum([i.total_seconds() for i in get_session_durations(state["log"])]) + (
            get_duration_of_ongoing_session(state["log"]) if state["running"] else 0)


# Print lock status: if it is locked and how long it has been locked
def print_lock_status(state):
    if lock.is_locked():
        if not lock.is_unlock_allowed(state):
            print(f"This session is locked. ({format_second(state['lock']['locked_for'])})")
            return
    print(f"This session is not locked")


# Get the total time locked in seconds
def get_total_time_locked(state):
    return state["lock"]["total_time_locked"]


