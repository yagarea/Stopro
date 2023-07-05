#!/usr/bin/env python

from os import geteuid, path, chdir
from commands import *
from args import get_args


def check_root():
    if geteuid() != 0:
        print("You need root permission")
        exit(1)


def main():
    arguments = get_args()
    config = load_yaml(arguments.config_path)
    if arguments.command == "start":
        check_root()
        cmd_start(arguments, config)
    elif arguments.command == "stop":
        check_root()
        cmd_stop(arguments, config)
    elif arguments.command == "lock":
        cmd_lock(arguments, config)
    elif arguments.command == "config":
        check_root()
        cmd_config(arguments, config)
    elif arguments.command == "status":
        cmd_status(arguments, config)
    elif arguments.command == "stats":
        cmd_stats(arguments, config)
    elif arguments.command == "clear-history":
        cmd_clear_history(arguments, config)


if __name__ == "__main__":
    main()

