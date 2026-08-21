#!/usr/bin/env python

from os import geteuid
from .commands import *
from .args import get_args
from .state import State



DEBUG = False

# Commands that write to /etc or to the state directory.
ROOT_COMMANDS = ("start", "stop", "config")
# Commands that read the configuration file.
CONFIG_COMMANDS = ("start", "stats")
# Commands that read or change the state file.
STATE_COMMANDS = ("start", "stop", "lock", "status", "stats", "clear-history")


def check_root():
    if geteuid() != 0:
        print("You need root permission")
        exit(1)


def main():
    arguments = get_args()
    command = arguments.command

    # Only "start" and "stats" read the config, so the other commands must not
    # fail when it is missing or unparsable.
    config = load_yaml(arguments.config_path) if command in CONFIG_COMMANDS else None

    if command in ROOT_COMMANDS:
        check_root()

    # Loading the state comes after the root check because it creates the state
    # file when it is missing, which an ordinary user is not allowed to do.
    state = State.load(debug=arguments.debug) if command in STATE_COMMANDS else None

    if command == "start":
        cmd_start(arguments, config, state)
    elif command == "stop":
        cmd_stop(arguments, config, state)
    elif command == "lock":
        cmd_lock(arguments, config, state)
    elif command == "config":
        cmd_config(arguments, config, state)
    elif command == "status":
        cmd_status(arguments, config, state)
    elif command == "stats":
        cmd_stats(arguments, config, state)
    elif command == "clear-history":
        cmd_clear_history(arguments, config, state)
    elif command == "version":
        from importlib.metadata import version
        print(version("stopro"))


if __name__ == "__main__":
    main()
