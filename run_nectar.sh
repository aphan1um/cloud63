#!/bin/bash

. ./openrc.sh; ansible-playbook --ask-become-pass -i hosts nectar.yaml $@