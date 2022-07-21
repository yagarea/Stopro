from utils import *

def cmd_start():
    backup_hosts()
    forbid_sites(config["forbidden_sites"])
    print("Your self control session started")


def cmd_stop():
    apply_backup()
    print("Your self control session ended")


def cmd_status():
    print("STATUS")


