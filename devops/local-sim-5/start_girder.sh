#!/bin/bash
# Start girder in the local-sim-5 container.  Unlike ../ver5/start_girder.sh,
# this runs as root (the container is privileged for apptainer) and does not
# need the DSA_USER / docker-socket handling, since jobs are executed with
# apptainer rather than docker.
set -euxo pipefail

PATH="/opt/venv/bin:/opt/digital_slide_archive/devops/dsa/utils:$PATH"

# Provisioning needs pyaml; unlike the Girder 3 provisioner, this provision.py
# does not import pkg_resources, so setuptools does not need to be downgraded.
pip install -q pyaml

echo ==== Pre-Provisioning ===
python /opt/digital_slide_archive/devops/dsa/provision.py -v --pre \
    --yaml "${DSA_PROVISION_YAML:-}"

echo ==== Provisioning ===
python /opt/digital_slide_archive/devops/dsa/provision.py -v --main \
    --yaml "${DSA_PROVISION_YAML:-}"

echo ==== Creating FUSE mount ===
girder mount ${DSA_GIRDER_MOUNT_OPTIONS:-} /fuse || true

echo ==== Starting Girder ===
girder serve --host=0.0.0.0 &
girder_pid=$!
until curl --silent http://localhost:8080/api/v1/system/version >/dev/null 2>/dev/null; do
    echo -n .
    sleep 1
done
echo

echo ==== Post-Provisioning ====
# This pulls the Slicer CLI images (as SIF files into SIF_IMAGE_PATH when the
# singularity flow is enabled) and registers the CLI tasks.
python /opt/digital_slide_archive/devops/dsa/provision.py -v --post \
    --yaml "${DSA_PROVISION_YAML:-}"

wait ${girder_pid}
