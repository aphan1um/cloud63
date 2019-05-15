# Ansible script
Allows automated deployment of our system.

## How to run:
Ensure you have [the latest version of Ansible installed](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html). The code should be run outside of Nectar instances (if outside unimelb campus run it with VPN).

1. Ensure you have the OpenStack API password and its RC file (rename it as *openrc.sh* and add it into this directory).

2. Ensure you have a private key to attach to each VM instance, named *pkey_team63.sh*.

3. Run code in terminal:
```
chmod +x run_nectar.sh
chmod 600 pkey_team63.pem

./run_nectar.sh
```
