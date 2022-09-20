from dateutil import parser
from datetime import timedelta, datetime
from rich import print


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
    return f"{int(days)} days {int(hours)} hours {int(minutes)} minutes {int(seconds)} seconds"


def print_session_status(is_running):
    if is_running:
        print("Self control session is [bold green]activated[/bold green]")
    else:
        print("Self control session is [bold red]not activated[/bold red]")


def print_global_stats(sessions: list, s_dur: list, is_running: bool):
    total_time = sum([i.total_seconds() for i in s_dur])
    session_count = (len(sessions) - (1 if is_running else 0))
    avg_time = total_time / session_count if session_count > 0 else 0
    longest_session = 0 if len(s_dur) == 0 else max([i.seconds for i in s_dur])

    print_session_status(is_running)

    print(f"[bold]Total time:[/bold]\t{format_second(total_time)}")
    print(f"[bold]Average time:[/bold]\t{format_second(avg_time)}")
    print(f"[bold]Total sessions:[/bold]\t{session_count}")
    print(f"[bold]Longest:[/bold]\t{format_second(longest_session)}")


def get_duration_of_ongoing_session(log):
    current_session_start = log[-1][0]
    return (datetime.now() - parser.parse(current_session_start)).total_seconds()
