from shutil import copy2
from subprocess import call

def backup_hosts():
    copy2("/etc/hosts", "/etc/hosts.stopro_backup", follow_symlinks=True)

def apply_backup():
    call("mv /etc/hosts.stopro_backup /etc/hosts", shell=True)

def forbid_sites(forbidden_sites):
    with open("/etc/hosts", "a") as hosts:
        hosts.write("\n\n# SELF CONTROL\n")
        for site in forbidden_sites:
            hosts.write(f"0.0.0.0 {site}\n0.0.0.0 www.{site}\n::0 {site}\n::0 www.{site}\n")

def print_help():
    print("help")

