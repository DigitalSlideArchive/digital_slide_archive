#!/bin/bash
set -euxo pipefail
. /opt/venv/bin/activate
pip install pyaml setuptools

echo ==== Pre-Provisioning ===
/opt/venv/bin/python3 /opt/provision.py --worker-pre -v --yaml /opt/provision.yaml
echo ==== Provisioning === &&
/opt/venv/bin/python3 /opt/provision.py --worker-main -v --yaml /opt/provision.yaml
echo ==== Starting Worker === &&
DOCKER_CLIENT_TIMEOUT=86400 TMPDIR=${TMPDIR:-/tmp} GW_DIRECT_PATHS=true celery -A girder_worker.app.app worker --concurrency=${DSA_WORKER_CONCURRENCY:-2} -Ofair --prefetch-multiplier=1
