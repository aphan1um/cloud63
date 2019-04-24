# README for Ansible
Automate creation of VMs and their purposes.

## How to run:
Ensure you have [Ansible installed](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html). The code should be run outside of Nectar instances (not sure if it can be run outside unimelb campus without VPN).

1. Remove the current openrc.sh and download your version by going to Nectar dashboard. Ensure you also have the password for OpenRC.

2. Run code in terminal:
```
chmod +x run_nectar.sh
./run_nectar.sh
```
