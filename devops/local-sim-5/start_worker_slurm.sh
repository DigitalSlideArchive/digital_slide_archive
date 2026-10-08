#!/bin/bash
# Start the girder_worker with slurm client access.  Mirrors the worker
# startup in ../ver5/start_worker.sh, plus munged so that the slurm client
# tools can authenticate against the slurm "cluster" container (both share
# the same munge key).
set -euxo pipefail

PATH="/opt/venv/bin:$PATH"

# Provisioning needs pyaml; unlike the Girder 3 provisioner, this provision.py
# does not import pkg_resources, so setuptools does not need to be downgraded.
pip install -q pyaml

# Start munged so slurm client tools can authenticate.
mkdir -p /run/munge /var/log/munge
cp /opt/munge.key /etc/munge/munge.key
chown munge:munge /etc/munge/munge.key /run/munge /var/log/munge
chmod 600 /etc/munge/munge.key
chmod 711 /etc/munge
chmod 755 /run/munge /var/log/munge
runuser -u munge -- munged
sleep 1

echo ==== Worker Pre-Provisioning ===
python /opt/digital_slide_archive/devops/dsa/provision.py -v --worker-pre \
    --yaml "${DSA_PROVISION_YAML:-}"

echo ==== Worker Provisioning ===
python /opt/digital_slide_archive/devops/dsa/provision.py -v --worker-main \
    --yaml "${DSA_PROVISION_YAML:-}"

echo ==== Starting Worker ===
exec celery -A girder_worker.app.app worker \
    --concurrency="${DSA_WORKER_CONCURRENCY:-2}" -Ofair --prefetch-multiplier=1
