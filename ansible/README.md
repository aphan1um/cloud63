
# Ansible script
Allows automated deployment of our system.

## How to run:
Ensure you have [the latest version of Ansible installed](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html). The code should be run outside of Nectar instances (if outside unimelb campus run it with VPN).
  
1. Ensure you have the OpenStack API password and its RC file (rename it to *openrc.sh* and add it into this directory).
2. Ensure you have a private key to attach to each VM instance, named *pkey_team63.pem*.
3. Run these commands in order, into terminal:

```
chmod +x run_nectar.sh
chmod 600 pkey_team63.pem
./run_nectar.sh
```

## Particular files in /ansible
* *files/docker-compose.yml*: The blueprint to running our components for our system. This can be tweaked so that you may run multiple harvesters, for instance.
* *files/couchdb_docs.tar.gz*: Compressed archive that contains the relevant documents and design documents to insert into newly created CouchDB database before running the Docker images. These contain files such as the five API keys, an AURIN dataset and design docs for our Tweets database.
* *host_vars/nectar.yaml*: Template for creating the VM instances, security groups and volumes. This can be modified to allow as many instances, with differing purposes, to be created, or change the name of your key-pair to use.
