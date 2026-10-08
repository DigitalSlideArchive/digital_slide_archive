#!/bin/bash
# Start the girder_worker in the local-sim container.  Mirrors the worker
# startup in ../ver5/start_worker.sh, but with the singularity plugin and
# without the docker-log forwarding.
set -euxo pipefail

PATH="/opt/venv/bin:$PATH"

# Provisioning needs yaml and pkg_resources (setuptools is no longer included
# in the venv by default).
pip install -q pyaml "setuptools<81"

echo ==== Worker Pre-Provisioning ===
python /opt/digital_slide_archive/devops/dsa/provision.py -v --worker-pre \
    --yaml "${DSA_PROVISION_YAML:-}"

echo ==== Worker Provisioning ===
python /opt/digital_slide_archive/devops/dsa/provision.py -v --worker-main \
    --yaml "${DSA_PROVISION_YAML:-}"

echo ==== Starting Worker ===
exec celery -A girder_worker.app.app worker \
    --concurrency="${DSA_WORKER_CONCURRENCY:-2}" -Ofair --prefetch-multiplier=1
