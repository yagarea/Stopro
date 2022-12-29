from dateutil import parser
from datetime import timedelta, datetime
from rich import print
import lock


def get_session_durations(sessions: list):
    output = list()
    for session in sessions:
        if session[1] != "+":
            start, end = parser.parse(session[0]), parser.parse(session[1])
            output.append((end - start))
    return output


def format_second(total_seconds: int):
    days = total_seconds // (60 * 60 * 24)
    hours = (total_seconds // 3600 ) % 24
    minutes = (total_seconds // 60) % 60
    seconds = total_seconds % 60
    output = ""
    if days > 0:
        output += f"{int(days)} day{'' if days == 1 else 's'} "
    if hours > 0:
        output += f"{int(hours)} hour{'' if hours == 1 else 's'} "
    if minutes > 0:
        output += f"{int(minutes)} minute{'' if minutes == 1 else 's'} "
    return output + f"{int(seconds)} second{'' if minutes == 1 else 's'}"


def print_session_status(state):
    if state["running"]:
        print("Self control session is [bold green]activated[/bold green]")
        print(f"[bold]Current session:[/bold]\t{format_second(get_duration_of_ongoing_session(state['log']))}")
        print_lock_status(state)
    else:
        print("Self control session is [bold red]not activated[/bold red]")


def get_longest_session(sessions: list):
    if len(sessions) == 0:
        return 0
    return max([i.total_seconds() for i in get_session_durations(sessions)])


def print_global_stats(state):
    total_time = get_total_time(state["log"])
    session_count = (len(state["log"]) - (1 if state["running"] else 0))
    avg_time = total_time / session_count if session_count > 0 else 0
    longest_session = get_longest_session(state["log"])

    print_session_status(state)
    print("")

    print(f"[bold]Total time:[/bold]\t{format_second(total_time)}")
    print(f"[bold]Average time:[/bold]\t{format_second(avg_time)}")
    print(f"[bold]Total sessions:[/bold]\t{session_count}")
    print(f"[bold]Longest:[/bold]\t{format_second(longest_session)}")


def get_duration_of_ongoing_session(log):
    current_session_start = log[-1][0]
    return (datetime.now() - parser.parse(current_session_start)).total_seconds()


def get_total_time(log):
    return sum([i.total_seconds() for i in get_session_durations(log)])



def print_lock_status(state):
    if lock.is_locked():
        if not lock.is_unlock_allowed(state):
            print(f"This session is locked. ({format_second(lock.get_remaining_time(state))} remaining)")
            return
    print(f"This session is not locked")


