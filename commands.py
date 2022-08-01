from utils import *
from os import environ
from subprocess import call
from stats import *

def cmd_start(arguments, config):
    backup_hosts()
    forbid_sites(config["forbidden_sites"])
    log_activity()
    if not arguments.silent_mode:
        print("Your self control session started")


def cmd_stop(arguments, config):
    apply_backup()
    log_activity()
    if not arguments.silent_mode:
        print("Your self control session ended")


def cmd_status(arguments, config):
    state = get_state()
    s_dur = get_session_durations(state["log"])
    print_global_stats(state["log"], s_dur, state["running"])

def cmd_config(arguments, config):
    editor = environ.get("$EDITOR", "/usr/bin/vim")
    call([editor, arguments.config_path])



