#!/bin/bash

. ./openrc.sh; ansible-playbook --skip-tags "setup_packages" --ask-become-pass -i hosts nectar.yaml