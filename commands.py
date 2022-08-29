from utils import *
from os import environ
from subprocess import call
from stats import *

def cmd_start(arguments, config):
    state = get_state()
    if state["running"]:
        print("A self control session is already in progress")
    else:
        backup_hosts()
        forbid_sites(config["forbidden_sites"])
        log_activity()
        if not arguments.silent_mode:
            print("Your self control session [bold green]started[/bold green]")


def cmd_stop(arguments, config):
    state = get_state()
    if state["running"]:
        apply_backup()
        log_activity()
        if not arguments.silent_mode:
            print("Your self control session [bold green]ended[/bold green]")
    else:
        print("No self control session is currently running")


def cmd_status(arguments, config):
    state = get_state()
    s_dur = get_session_durations(state["log"])
    print_global_stats(state["log"], s_dur, state["running"])

def cmd_config(arguments, config):
    editor = environ.get("$EDITOR", "/usr/bin/vim")
    call([editor, arguments.config_path])
