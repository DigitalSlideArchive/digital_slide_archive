#!/bin/bash
# Ensures that the main process runs as the DSA_USER and is part of both that
# group and the docker group.  Fail if DSA_USER is not specified.
if [[ -z "$DSA_USER" ]]; then
  echo "Set the DSA_USER before starting (e.g, DSA_USER=\$$(id -u):\$$(id -g) <up command>"
  exit 1
fi
# add a user with the DSA_USER's id; this user is named ubuntu if it doesn't
# exist.
adduser --uid ${DSA_USER%%:*} --disabled-password --gecos "" ubuntu 2>/dev/null
# add a group with the DSA_USER's group id.
addgroup --gid ${DSA_USER#*:} $(id -ng ${DSA_USER#*:}) 2>/dev/null
# add the user to the user group.
adduser $(id -nu ${DSA_USER%%:*}) $(getent group ${DSA_USER#*:} | cut "-d:" -f1) 2>/dev/null
# add a group with the docker group id.
addgroup --gid $(stat -c "%g" /var/run/docker.sock) docker 2>/dev/null
# add the user to the docker group.
adduser $(id -nu ${DSA_USER%%:*}) $(getent group $(stat -c "%g" /var/run/docker.sock) | cut "-d:" -f1) 2>/dev/null
# Try to increase permissions for the docker socket; this helps this work on
# OSX where the users don't translate
chmod 777 /var/run/docker.sock 2>/dev/null || true
chmod 777 ${TMPDIR:-/tmp} || true
echo ==== Pre-Provisioning ===
python3 /opt/digital_slide_archive/devops/dsa/provision.py --worker-pre
echo ==== Provisioning === &&
python3 /opt/digital_slide_archive/devops/dsa/provision.py --worker-main
echo ==== Starting Worker === &&
# Run subsequent commands as the DSA_USER.  This sets some paths based on what
# is expected in the Docker so that the current python environment and the
# devops/dsa/utils are available.  Then it runs girder_worker
su $(id -nu ${DSA_USER%%:*}) -c "
  PATH=\"/opt/digital_slide_archive/devops/dsa/utils:/opt/venv/bin:/.pyenv/bin:/.pyenv/shims:$PATH\";
  DOCKER_CLIENT_TIMEOUT=86400 TMPDIR=${TMPDIR:-/tmp} GW_DIRECT_PATHS=true python -m girder_worker --concurrency=${DSA_WORKER_CONCURRENCY:-2} -Ofair --prefetch-multiplier=1
"
