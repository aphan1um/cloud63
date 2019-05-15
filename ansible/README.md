# Ansible script
Allows automated deployment of our system.

In particular, running the Ansible script visibly creates:
1. A functioning website as shown in video demo.
2. At least one Twitter harvester.
3. A clustered CouchDB database.
4. A Docker visualiser at port 8080 (to state of containers running at different nodes).

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

## Particular files in /ansible
* *files/docker-compose.yml*: The blueprint to running our components for our system. This can be tweaked so that you may more than one Twitter harvester, when the Ansible script is being executed.

* *files/couchdb_docs.tar.gz*: Compressed archive containing relevant documents & design docs to insert into the newly created CouchDB database before running the Docker images. Compressed so that it may be easily downloadable into VM instance delegated to insert documents during Ansible script execution. File contents:
	* *queries_couchdb.json*: Set of documents containing the 189 queries to use for running Twitter harvesters.
	* *aurin_couchdb.json*: Contains the AURIN dataset to be inserted into *aurin_lga* database.
	* *api_keys_couchdb.json*: Has 5 API keys to be used between the harvesters.
	* *tweets_designdoc.json*: Design documents for the *tweets_final* database, containing views such as number of 'good/bad' food tweets within different Australian states.
	* *geocodes_dd.json*: Design documents for *geocodes_final* database. Has a view that displays all location names (and aliases) currently within this database.

* *host_vars/nectar.yaml*: Template for creating the VM instances, security groups and volumes. This can be modified to allow as many instances, with differing purposes, to be created, or change the name of your key-pair to use. **Note: At least one batch instance should be a manager, since Docker Swarm requires at least one manager to create the swarm.**

## Interacting with Nectar instances afterwards
### Interacting with CouchDB database
One may want to interact with the Fauxton interface with any of the VM instances that had a CouchDB database installed. For instance, to interactively add more queries to database *tweet_queries* so some Twitter harvester will search this query whilst running.

In this case, access it via secure port forwarding to 5984 with SSH. Example:

```
ssh -L 5984:localhost:5984 -i pkey_team63.pem ubuntu@<Nectar IP address with CouchDB installed>
```
Thereafter you may access Fauxton via your web-browser with address ```http://localhost:5984``` with username ```user``` and password ```pass``` (based on current Ansible configuration).

### Scaling Docker services
You may want to modify the workload of your Twitter harvesters or the replicas of the front-end website that should be running. In that case, one may SSH into any Docker manager node (with the private key) and execute this commands:

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


