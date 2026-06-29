#!/bin/bash
set -euxo pipefail

. /opt/venv/bin/activate
pip install pyaml setuptools

echo ==== Pre-Provisioning ===
python /opt/provision.py -v --pre --yaml /opt/provision.yaml

echo ==== Provisioning ===
python /opt/provision.py -v --main --yaml /opt/provision.yaml

echo ==== Creating FUSE mount ===
girder mount ${DSA_GIRDER_MOUNT_OPTIONS:-} /fuse || true

echo ==== Starting Local Worker ===
celery -A girder_worker.app worker -Q local --concurrency 4 &

echo ==== Starting Girder ===
girder serve --host=0.0.0.0 &
girder_pid=$!
until curl --silent http://localhost:8080/api/v1/system/version >/dev/null 2>/dev/null; do
  echo -n .
  sleep 1
done

echo ==== Postprovisioning ===
python /opt/provision.py -v --post --yaml /opt/provision.yaml

wait ${girder_pid}
