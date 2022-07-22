from utils import *
from os import environ
from subprocess import call

def cmd_start(arguments, config):
    backup_hosts()
    forbid_sites(config["forbidden_sites"])
    if not arguments.silent_mode:
        print("Your self control session started")


def cmd_stop(arguments, config):
    apply_backup()
    if not arguments.silent_mode:
        print("Your self control session ended")


def cmd_status(arguments, config):
    print("STATUS")

def cmd_config(arguments, config):
    editor = environ.get("EDITOR", "/usr/bin/vim")
    call([editor, config.config_path])



