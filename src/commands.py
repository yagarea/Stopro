from utils import *
from os import environ
from subprocess import call
from stats import *
from rich import print
from rich.console import Console
from rich.columns import Columns
from achievments import get_achievements
import lock


def cmd_start(arguments, config):
    state = get_state()
    if state["running"]:
        print("A self control session is already in progress")
    else:
        backup_hosts()
        forbid_sites(config["forbidden_sites"])
        if not arguments.silent_mode:
            print("Your self control session [bold green]started[/bold green]")

        if arguments.locked_for != "":
            time_in_seconds = lock.parse_lock_time(arguments.locked_for)
            state = lock.lock(state, time_in_seconds)
        log_activity(state)


def cmd_stop(arguments, config):
    state = get_state(debug=arguments.debug)
    if state["running"]:
        if lock.is_locked() and not lock.is_unlock_allowed(state):
            print("This session is locked. You can not stop it.")
            return
        apply_backup()
        state = lock.unlock(state)
        log_activity(state)
        if not arguments.silent_mode:
            print("Your self control session [bold green]ended[/bold green]")
    else:
        print("No self control session is currently running")


def cmd_lock(arguments, config):
    state = get_state()
    if not state["running"]:
        print("No self control session is currently running")
        return
    if state["lock"]["is_locked"] and lock.get_remaining_time(state) > 0:
        print("This session is already locked")
        return
    time_in_seconds = lock.parse_lock_time(arguments.locked_for)
    state = lock.lock(state, time_in_seconds)
    save_state(state)


def cmd_stats(arguments, config):
    cmd_status(arguments, config)
    state = get_state()
    print_global_stats(state)

    print("\n", end="")

    console = Console()
    console.print(Columns(get_achievements(config), equal=True, expand=True))


def cmd_config(arguments, config):
    editor = environ.get("$EDITOR", "/usr/bin/vim")
    call([editor, arguments.config_path])


def cmd_clear_history(arguments, config):
    state = get_state()
    if state["running"]:
        print("You can not clear history during self control session. To continue stop current session and try again.")
    else:
        print("Are you sure you want to clear your history ? [red](this is permanent)[/red] [bold][Y/N][/bold] ")
        answer = str(input()).lower()
        if answer in ("yes", "y"):
            create_new_clean_state()
            print("History was successfully deleted")


def cmd_status(arguments, config):
    state = get_state()
    print_session_status(state)
    if not state["running"]:
        return
    if state["lock"]["is_locked"] and lock.get_remaining_time(state) > 0:
        lock.static_progressbar(state)
