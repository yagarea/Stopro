from shutil import copy2
from subprocess import call, check_output
import yaml

# Basics

def print_help():
    print("help")

def load_config(config_path):
    try:
        with open(config_path, 'r') as stream:
            raw_config = yaml.safe_load(stream)
            return raw_config
    except yaml.YAMLError:
        print_error(f"Yaml parse of {config_file_path} failed")
        exit(1)
    except IOError:
        print_error(f"File {config_file_path} does not exists")
        exit(1)


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

