from utils import *
from os import environ
from subprocess import call

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
    if state["running"]:
        print("Self control session is activated")
    else:
        print("Self control session is not activated")

def cmd_config(arguments, config):
    editor = environ.get("$EDITOR", "/usr/bin/vim")
    call([editor, arguments.config_path])



