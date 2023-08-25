from shutil import copy2
from subprocess import call, check_output
from os import path
from datetime import datetime
import yaml
from functools import cache


STATE_PATH = "/usr/share/stopro/state.yml"

# Basics

# load yaml file to dictionary
def load_yaml(yaml_path, debug=False):
    try:
        with open(yaml_path, 'r') as stream:
            raw_yaml = yaml.safe_load(stream)
            if debug:
                print(f"Loaded yaml from {yaml_path}")
                print(raw_yaml)
            return raw_yaml
    except yaml.YAMLError:
        print(f"Yaml parse of {yaml_path} failed\nPlease check syntax")
        exit(1)
    except IOError:
        print(f"File {yaml_path} does not exists")
        exit(1)


def write_yaml(yaml_content, file_path):
    try:
        with open(file_path, "w") as yaml_file:
            yaml_file.write(yaml.dump(yaml_content))
    except yaml.YAMLError:
        print_error(f"Yaml parse of {yaml_path} failed\nPlease check syntax")
        exit(1)
    except IOError:
        print_error(f"Error occurred while writing to {yaml_path}")
        exit(1)

# create new clean state
def create_new_clean_state():
    clean_state = dict()
    clean_state["log"] = list()
    clean_state["running"] = False
    clean_state["lock"] = {"is_locked": False, "locked_for": 0, "locked_since": 0, "total_time_locked": 0}
    write_yaml(clean_state, STATE_PATH)
    return clean_state

# load stopro state
@cache
def get_state(debug=False):
    if path.isfile(STATE_PATH):
        return load_yaml(STATE_PATH, debug)
    else:
        return create_new_clean_state()


def save_state(state):
    write_yaml(state, STATE_PATH)


def log_activity(state):
    if state["running"]:                        # is running
        state["running"] = False
        if len(state["log"]) > 0:
            state["log"][-1][1] = str(datetime.now())
        else:
            print("log corrupted")
            state["log"].append(["?", str(datetime.now())])
    else:                                       # is not running
        state["running"] = True
        state["log"].append([str(datetime.now()), "+"])
    write_yaml(state, STATE_PATH)


# Blocking sites functions
def backup_hosts():
    copy2("/etc/hosts", "/etc/hosts.stopro_backup", follow_symlinks=True)


def apply_backup():
    call("mv /etc/hosts.stopro_backup /etc/hosts", shell=True)


def forbid_sites(forbidden_sites):
    with open("/etc/hosts", "a") as hosts:
        hosts.write("\n\n# SELF CONTROL\n")
        for site in forbidden_sites:
            hosts.write(f"0.0.0.0 {site}\n0.0.0.0 www.{site}\n::0 {site}\n::0 www.{site}\n")


def format_second(total_seconds: int) -> str:
    days = total_seconds // (60 * 60 * 24)
    hours = (total_seconds // 3600 ) % 24
    minutes = (total_seconds // 60) % 60
    seconds = total_seconds % 60
    output = ""

    if total_seconds == 0:
        return "0 seconds"

    if days > 0:
        output += f"{int(days)} day{'' if days == 1 else 's'} "
    if hours > 0:
        output += f"{int(hours)} hour{'' if hours == 1 else 's'} "
    if minutes > 0:
        output += f"{int(minutes)} minute{'' if minutes == 1 else 's'} "
    if seconds > 0:
        output += f"{int(seconds)} second{'' if seconds == 1 else 's'}"
    return output.strip()

