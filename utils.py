from shutil import copy2
from subprocess import call, check_output
from os import path
from datetime import datetime
import yaml

STATE_PATH = "/usr/share/stopro/state.yml"

# Basics

# load yaml file to dictionary
def load_yaml(yaml_path):
    try:
        with open(yaml_path, 'r') as stream:
            raw_yaml = yaml.safe_load(stream)
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


# load stopro state
def get_state():
    if path.isfile(STATE_PATH):
        return load_yaml(STATE_PATH)
    else:
        clean_state = dict()
        clean_state["log"] = list()
        clean_state["running"] = False
        write_yaml(clean_state, STATE_PATH)
        return clean_state


def log_activity():
    state = get_state()
    if state["running"]:                        # is running
        state["running"] = False
        if len(state["log"]) > 0:
            state["log"][-1][1] = datetime.now()
        else:
            print("log corrupted")
            state["log"].append(["?", datetime.now()])
    else:                                       # is not running
        state["running"] = True
        state["log"].append([datetime.now(), "+"])
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
















# Not decided if funny or cringe
def emergency_stop_verification():
    answer = input("Are you sure this is emergency ? [y/n]\n")
    if answer.lower() not in ["y", "yes"]:
        exit(0)
    answer = input("Really ? [y/n]\n")
    if answer.lower() not in ["y", "yes"]:
        exit(0)
    answer = input("Isn't it really just a dull attempt to satisfy your internet addiction?  ? [y/n]\n") 
    if answer.lower() not in ["y", "yes"]:
        exit(0)
    answer = input("Than beg!\n")
    if len(answer) < 30:
        print("Not good enough")
        exit(0)
    print("Accepted")


