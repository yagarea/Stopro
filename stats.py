from dateutil import parser
from datetime import timedelta
from rich import print

def get_session_durations(sessions: list):
    output = list()
    for i in range(len(sessions)):
        if sessions[i][1] != "+":
            start, end = parser.parse(sessions[i][0]), parser.parse(sessions[i][1])
            output.append((end - start))
    return output


def format_seccond(seconds: int):
    td = timedelta(0, 0, seconds)
    days = td.days
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{int(days)} days {int(hours)} hours {int(minutes)} minutes {int(seconds)} seconds"


def print_global_stats(sessions: list, s_dur: list, is_running: bool):
    total_time = sum([i.seconds for i in s_dur])
    session_count = (len(sessions) - (1 if is_running else 0))
    avg_time = total_time / session_count


    if is_running:
        print("Self control session is [bold green]activated[/bold green]")
    else:
        print("Self control session is [bold red]not activated[/bold red]")

    print(f"[bold]Total time:[/bold]\t{format_seccond(total_time)}")
    print(f"[bold]Average time:[/bold]\t{format_seccond(avg_time)}")
    print(f"[bold]Total sessions:[/bold]\t{session_count}")

