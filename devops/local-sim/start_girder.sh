#!/bin/bash
# Start girder in the local-sim container.  Unlike ../dsa/start_girder.sh,
# this runs as root (the container is privileged for apptainer) and does not
# need the DSA_USER / docker-socket handling, since jobs are executed with
# apptainer rather than docker.
set -euxo pipefail

PATH="/opt/venv/bin:/opt/digital_slide_archive/devops/dsa/utils:$PATH"

# Provisioning needs yaml and pkg_resources (setuptools is no longer included
# in the venv by default).
pip install -q pyaml "setuptools<81"

echo ==== Pre-Provisioning ===
python /opt/digital_slide_archive/devops/dsa/provision.py -v --pre --no-wait \
    --yaml "${DSA_PROVISION_YAML:-}"

echo ==== Provisioning ===
python /opt/digital_slide_archive/devops/dsa/provision.py -v --main \
    --yaml "${DSA_PROVISION_YAML:-}"

echo ==== Creating FUSE mount ===
girder mount ${DSA_GIRDER_MOUNT_OPTIONS:-} /fuse || true

echo ==== Starting Girder ===
exec girder serve
