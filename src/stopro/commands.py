from .utils import *
from os import environ
from subprocess import call
import shlex
from .stats import *
from rich import print
from rich.console import Console
from rich.columns import Columns
from .achievments import get_achievements
from . import lock



def print_invalid_lock_time(error):
    print(f"[bold red]Error:[/bold red] {error}")


# start command
def cmd_start(arguments, config, state):
    if state.is_running:
        print("A self control session is already in progress")
        return

    time_in_seconds = None
    if arguments.locked_for != "":
        try:
            time_in_seconds = lock.parse_lock_time(arguments.locked_for)
        except lock.InvalidLockTime as error:
            print_invalid_lock_time(error)
            return

    backup_hosts()
    forbid_sites(config["forbidden_sites"])
    if not arguments.silent_mode:
        print("Your self control session [bold green]started[/bold green]")

    state.start(locked_for=time_in_seconds)


# stop command
def cmd_stop(arguments, config, state):
    if state.is_running:
        if not state.is_unlock_allowed:
            print("This session is locked. You can not stop it.")
            return
        # The result is verified against the hosts file itself instead of the
        # return value: a backup taken while the sites were already blocked
        # restores "successfully" but still leaves them blocked.
        apply_backup()
        if is_hosts_blocked():
            print_error(
                f"{HOSTS_PATH} still blocks the forbidden sites after restoring the backup.\n"
                f"The session stays active. Repair {HOSTS_PATH} manually and run 'stopro stop' again.")
            return
        state.stop()
        if not arguments.silent_mode:
            print("Your self control session [bold green]ended[/bold green]")
    else:
        print("No self control session is currently running")


# lock command
def cmd_lock(arguments, config, state):
    if not state.is_running:
        print("No self control session is currently running")
        return
    if state.is_locked and state.remaining_lock_time > 0:
        print("This session is already locked")
        return
    try:
        time_in_seconds = lock.parse_lock_time(arguments.locked_for)
    except lock.InvalidLockTime as error:
        print_invalid_lock_time(error)
        return
    state.lock(time_in_seconds)


# statistics command
def cmd_stats(arguments, config, state):
    cmd_status(arguments, config, state)
    print_global_stats(state)

    print("\n", end="")

    console = Console()
    console.print(Columns(get_achievements(state, config), equal=True, expand=True))


# config command
def cmd_config(arguments, config, state):
    editor = environ.get("EDITOR") or "/usr/bin/vim"
    try:
        call(shlex.split(editor) + [arguments.config_path])
    except OSError as error:
        print_error(f"Could not start editor '{editor}'\n{error}")
        exit(1)


# clear command
def cmd_clear_history(arguments, config, state):
    if state.is_running:
        print("You can not clear history during self control session. To continue stop current session and try again.")
    else:
        print("Are you sure you want to clear your history ? [red](this is permanent)[/red] [bold][Y/N][/bold] ")
        answer = str(input()).lower()
        if answer in ("yes", "y"):
            state.clear()
            print("History was successfully deleted")


# status command
def cmd_status(arguments, config, state):
    print_session_status(state)
    if not state.is_running:
        return
    if state.is_locked and state.remaining_lock_time > 0:
        lock.static_progressbar(state)

