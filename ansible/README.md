

# Ansible script
Allows automated deployment of our system.

In particular, running the Ansible script visibly creates:
1. A functioning website as shown in video demo.
2. At least one Twitter harvester.
3. A clustered CouchDB database.
4. A Docker visualiser at port 8080 (to state of containers running at different nodes).

Note that with the current *docker-compose.yml* setup (which runs one Docker website container), you are able to access the website at any of the created VM instances due to the [routing mesh used by Docker](https://docs.docker.com/engine/swarm/ingress/). 

## How to run:
Ensure you have [the latest version of Ansible installed](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html). The code should be run outside of Nectar instances; if outside unimelb campus run it with VPN.
  
1. Ensure you have the OpenStack API password and its RC file (rename it to *openrc.sh* and add it into this directory).
2. Ensure you have a private key to attach to each VM instance, named *pkey_team63.pem*.
3. Run these commands into terminal:

```
chmod +x run_nectar.sh
chmod 600 pkey_team63.pem
./run_nectar.sh
```
You may be prompted for Openstack password and SUDO password. Note that you may ignore *chmod* commands if the 2 files already have appropriate permissions.

Below this page are additional documentation details on customising the setup that would be too long to mention in the report.

## Particular files in /ansible
***files/docker-compose.yml***: The "blueprint" to running our components for our system; a Docker Compose file. This can be tweaked so that you may more than one Twitter harvester for example, so Ansible script will deploy them when executed.

***files/couchdb_docs.tar.gz***: Compressed archive containing relevant documents & design docs to insert into the newly created CouchDB database before running the Docker images. Compressed so that it may be easily downloadable into VM instance delegated to insert documents during Ansible script execution.

File contents:
* *queries_couchdb.json*: Set of documents containing the 189 queries to use for running Twitter harvesters.
* *aurin_couchdb.json*: Contains the AURIN dataset to be inserted into *aurin_lga* database.
* *api_keys_couchdb.json*: Has 5 API keys to be used between the harvesters.
* *tweets_designdoc.json*: Design documents for the *tweets_final* database, containing views such as number of 'good/bad' food tweets within different Australian states.
* *geocodes_dd.json*: Design documents for *geocodes_final* database. Has a view that displays all location names (and aliases) currently within this database.

***host_vars/nectar.yaml***: Template for creating the VM instances, security groups and volumes. This can be modified to allow as many instances, with differing purposes, to be created, or change the name of your key-pair to use. Example:
```
instances:
  - name: leaders
    amount: 2
    groups: ['managers']
    volumes: []
  - name: manager_all
    amount: 5
    groups: ['managers', 'db', 'web']
    volumes: ['volDatabase', 'volManager']
  - name: worker_dbs
    amount: 10
    groups: ['workers', 'db']
    volumes: ['volDatabase']
```
This would create in total 17 Nectar VM instances (assuming your project is permitted to create this much):
*  Two (Swarm) manager nodes with no volumes named ```leaders-1``` and ```leaders-2```.

* Five manager nodes named ```manager_all-1, ... manager_all-5```, and attached volumes named after them as defined in ```volume_templates```. Each of the five nodes also have [Docker node labels](https://docs.docker.com/engine/reference/commandline/node_update/#add-label-metadata-to-a-node) ```db``` and ```web```, so they will have CouchDB databases installed and be able to run a front-end website in the swarm. 
 So we would have ```mangager_all-1``` have 2 volumes be attached: ```mangager_all-1_volDatabase``` and ```manager_all-1_volManager```. They will also need to be mounted afterwards, which can be arranged within the Ansible script.
 * Ten worker nodes named ```worker_dbs-1, ..., worker_dbs-10``` that each have a CouchDB database, to be part of a cluster, as well as a volume they can mount to.

All of the 17 instances, to be part of a swarm, are able to load Twitter harvesters (not requiring certain a Docker label). Security groups, key name to use and instance image to use are shared with all of these 17 instances.

Note: At least one batch instance should be a manager, since Docker Swarm requires at least one manager to create the swarm.

## Interacting with Nectar instances afterwards
### Interacting with CouchDB database
One may want to interact with the Fauxton interface with any of the VM instances that had a CouchDB database installed. For example, to interactively add more queries to database *tweet_queries* so some Twitter harvester will search this query whilst running. Another example is to add/remove Twitter API keys within the *api_keys* database.

In this case, access it via secure port forwarding to 5984 with SSH. Example:

```
ssh -L 5984:localhost:5984 -i pkey_team63.pem ubuntu@<Nectar IP address with CouchDB installed>
```
Thereafter you may access Fauxton via your web-browser with address ```http://localhost:5984``` with username ```user``` and password ```pass``` (based on current Ansible configuration). You may also decide to use the address to access the clustered database directly via CouchDB's REST API. 

### Scaling Docker services
You may want to modify the workload of your Twitter harvesters or the replicas of the front-end website that should be running. In that case, one may SSH into any Docker manager node (with the private key) and execute these commands:

```
# SSH into VM (Docker manager) node
ssh -i pkey_team63.pem ubuntu@<manager node IP>


# Display all containers running over the swarm
sudo docker service ls

# Stop Twitter harvesting (so to stop CouchDB indexing views with new Tweets;
# keep websites responsive).
sudo docker service scale test_twitscript=0

# Increase amount of harvesters running to 6 (5 API keys in DB means one API key set
# will be used by 2 harvester processes. Good idea is to increase # of API keys
# to improve Twitter scraping rate).
sudo docker service scale test_twitscript=6

# Increase # of copies of front-end website running to 3.
sudo docker service scale test_website=3
```

Refer to Docker docs for more info on how to interact with these Docker services. 


