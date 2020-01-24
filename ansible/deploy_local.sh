#!/bin/bash

if [ $(lsb_release -cs) != "bionic" ]; then
  echo "This script will only work on Ubuntu Ubuntu 18.04"
  return 1 || exit 1
fi

export GIRDER_EXEC_USER=`id -u -n`
export WORKER_EXEC_USER=`id -u -n`
ansible-galaxy install -r requirements.yml -p roles/
ansible-playbook -i inventory/local deploy_local.yml
