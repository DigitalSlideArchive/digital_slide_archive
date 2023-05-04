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
# Use iptables to make some services appear as if they are on localhost (as
# well as on the docker network).  This is done to allow tox tests to run.
sysctl -w net.ipv4.conf.eth0.route_localnet=1
iptables -t nat -A OUTPUT -o lo -p tcp -m tcp --dport 27017 -j DNAT --to-destination `dig +short mongodb`:27017
iptables -t nat -A OUTPUT -o lo -p tcp -m tcp --dport 11211 -j DNAT --to-destination `dig +short memcached`:11211
iptables -t nat -A POSTROUTING -o eth0 -m addrtype --src-type LOCAL --dst-type UNICAST -j MASQUERADE
echo 'PATH="/opt/digital_slide_archive/devops/dsa/utils:/opt/venv/bin:/.pyenv/bin:/.pyenv/shims:$PATH"' >> /home/$(id -nu ${DSA_USER%%:*})/.bashrc
echo ==== Pre-Provisioning ===
PATH="/opt/venv/bin:/.pyenv/bin:/.pyenv/shims:$PATH" \
python /opt/digital_slide_archive/devops/dsa/provision.py -v --pre
# Run subsequent commands as the DSA_USER.  This sets some paths based on what
# is expected in the Docker so that the current python environment and the
# devops/dsa/utils are available.  Then:
# - Provision the Girder instance.  This sets values in the database, such as
#   creating an admin user if there isn't one.  See the provision.py script for
#   the details.
# - If possible, set up a girder mount.  This allows file-like access of girder
#   resources.  It requires the host to have fuse installed and the docker
#   container to be run with enough permissions to use fuse.
# - Start the main girder process.
su $(id -nu ${DSA_USER%%:*}) -c "
  PATH=\"/opt/digital_slide_archive/devops/dsa/utils:/opt/venv/bin:/.pyenv/bin:/.pyenv/shims:$PATH\";
  echo ==== Provisioning === &&
  python /opt/digital_slide_archive/devops/dsa/provision.py -v --main &&
  echo ==== Creating FUSE mount === &&
  (girder mount /fuse || true) &&
  echo ==== Starting Girder === &&
  girder serve --dev
"
