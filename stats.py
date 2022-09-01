from dateutil import parser
from datetime import timedelta
from rich import print


def get_session_durations(sessions: list):
    output = list()
    for session in sessions:
        if session[1] != "+":
            start, end = parser.parse(session[0]), parser.parse(session[1])
            output.append((end - start))
    return output


def format_seccond(seconds: int):
    td = timedelta(0, 0, seconds)
    days = td.days
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{int(days)} days {int(hours)} hours {int(minutes)} minutes {int(seconds)} seconds"


def print_session_status(is_running):
    if is_running:
        print("Self control session is [bold green]activated[/bold green]")
    else:
        print("Self control session is [bold red]not activated[/bold red]")


def print_global_stats(sessions: list, s_dur: list, is_running: bool):
    total_time = sum([i.seconds for i in s_dur])
    session_count = (len(sessions) - (1 if is_running else 0))
    avg_time = total_time / session_count if session_count > 0 else 0
    longest_session = 0 if len(s_dur) == 0 else max([i.seconds for i in s_dur])

    print_session_status(is_running)

    print(f"[bold]Total time:[/bold]\t{format_seccond(total_time)}")
    print(f"[bold]Average time:[/bold]\t{format_seccond(avg_time)}")
    print(f"[bold]Total sessions:[/bold]\t{session_count}")
    print(f"[bold]Longest:[/bold]\t{format_seccond(longest_session)}")

