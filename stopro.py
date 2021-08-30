#!/usr/bin/env python

import yaml
from os import geteuid, path, chdir
from sys import argv
from utils import *

CONFIG_PATH = "/home/john/.config/stopro/conf.yml"

def check_root():
    if geteuid() != 0:
        print("You need root permission")
        exit(1)

def load_config():
    try:
        with open(CONFIG_PATH, 'r') as stream:
            raw_config = yaml.safe_load(stream)
            return raw_config
    except yaml.YAMLError:
        print_error(f"Yaml parse of {config_file_path} failed")
        exit(1)
    except IOError:
        print_error(f"File {config_file_path} does not exists")
        exit(1)


def main():
    check_root()
    config = load_config()
    command = argv[1].lower()
    if command == "start":
        backup_hosts()
        forbid_sites(config["forbidden_sites"])
    elif command == "stop":
        apply_backup()
    else:
        print_help()



if __name__ == "__main__":
    main()
