#!/bin/bash

. ./openrc.sh; ansible-playbook --skip-tags "couchdb,swarm" --ask-become-pass -i hosts nectar.yaml