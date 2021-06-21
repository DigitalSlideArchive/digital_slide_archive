#!/usr/bin/env bash

set -e

OLDSTART=$(curl --silent 'http://127.0.0.1:8080/api/v1/system/version')
girder build --dev
touch /etc/girder.cfg
echo "Girder has been rebuilt and will now restart"
while true; do NEWSTART=$(curl --silent 'http://127.0.0.1:8080/api/v1/system/version' || true); if [ "${OLDSTART}" != "${NEWSTART}" ]; then echo ${NEWSTART} | grep -q 'release' && break || true; fi; sleep 1; echo -n "."; done
echo ""
echo "Girder has restarted"
