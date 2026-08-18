from shutil import copy2, move
from subprocess import call, check_output
from os import path, makedirs
from datetime import datetime
import yaml
from functools import cache
from rich import print


STATE_PATH = "/usr/share/stopro/state.yml"
HOSTS_PATH = "/etc/hosts"
HOSTS_BACKUP_PATH = "/etc/hosts.stopro_backup"
BLOCK_MARKER = "# SELF CONTROL"

# Load yaml file to dictionary
def load_yaml(yaml_path, debug=False):
    try:
        with open(yaml_path, 'r') as stream:
            raw_yaml = yaml.safe_load(stream)
            if debug:
                print(f"Loaded yaml from {yaml_path}")
                print(raw_yaml)
            return raw_yaml
    except yaml.YAMLError:
        print_error(f"Yaml parse of {yaml_path} failed\nPlease check syntax")
        exit(1)
    except IOError:
        print_error(f"File {yaml_path} does not exists")
        exit(1)


# Save dictionary to yaml file
def write_yaml(yaml_content, file_path):
    try:
        with open(file_path, "w") as yaml_file:
            yaml_file.write(yaml.dump(yaml_content))
    except yaml.YAMLError:
        print_error(f"Yaml parse of {file_path} failed\nPlease check syntax")
        exit(1)
    except IOError:
        print_error(f"Error occurred while writing to {file_path}")
        exit(1)


# create new clean state
def create_new_clean_state():
    clean_state = dict()
    clean_state["log"] = list()
    clean_state["running"] = False
    clean_state["lock"] = {"is_locked": False,
                           "locked_for": 0,
                           "locked_since": 0,
                           "total_time_locked": 0}
    create_state_directory()
    write_yaml(clean_state, STATE_PATH)
    return clean_state


# Make sure the directory holding the state file exists
def create_state_directory():
    state_directory = path.dirname(STATE_PATH)
    if not state_directory:
        return
    try:
        makedirs(state_directory, exist_ok=True)
    except OSError as error:
        print_error(f"Could not create state directory {state_directory}\n{error}")
        exit(1)

# load stopro state
@cache
def get_state(debug=False):
    if path.isfile(STATE_PATH):
        return load_yaml(STATE_PATH, debug)
    else:
        return create_new_clean_state()

# save stopro state
def save_state(state):
    write_yaml(state, STATE_PATH)


# Write current state to state file
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
    copy2(HOSTS_PATH, HOSTS_BACKUP_PATH, follow_symlinks=True)


# Apply backup hosts file. Returns False when it could not be restored.
def apply_backup() -> bool:
    if not path.isfile(HOSTS_BACKUP_PATH):
        return False
    try:
        move(HOSTS_BACKUP_PATH, HOSTS_PATH)
    except OSError as error:
        print_error(f"Could not restore {HOSTS_PATH} from {HOSTS_BACKUP_PATH}\n{error}")
        return False
    return True


# Check whether the blocking rules are still present in the hosts file
def is_hosts_blocked() -> bool:
    try:
        with open(HOSTS_PATH, "r") as hosts:
            return BLOCK_MARKER in hosts.read()
    except IOError:
        return False


# Forbid sites by adding rules to /etc/hosts
def forbid_sites(forbidden_sites):
    with open(HOSTS_PATH, "a") as hosts:
        hosts.write(f"\n\n{BLOCK_MARKER}\n")
        for site in forbidden_sites:
            hosts.write(f"0.0.0.0 {site}\n0.0.0.0 www.{site}\n::0 {site}\n::0 www.{site}\n")


# Format total seconds to human readable format
def format_second(total_seconds: float) -> str:
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


# Print error message
def print_error(message):
    print(f"[bold red]ERROR:[/bold red]\t{message}")

