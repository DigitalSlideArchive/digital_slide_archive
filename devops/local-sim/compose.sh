#!/bin/bash
# Run docker compose for the local simulation.
#
# Compose is executed inside a helper container with the docker socket and
# the host project directory bind-mounted AT ITS HOST PATH.  The same-path
# bind is required: compose resolves bind-mount sources relative to the
# project directory as seen by the compose process, and the docker daemon
# resolves those sources on the host filesystem.  If the project were mounted
# at a different path (e.g., /work), the recorded bind sources would not
# resolve on the host.  Run deploy.sh first to put the project there.
#
# Examples:
#   ./compose.sh up -d
#   ./compose.sh logs -f girder
#   ./compose.sh down
set -euo pipefail
cd "$(dirname "$0")"

HOST_DIR="${DSA_SIM_HOST_DIR:-/home/ubuntu/dsa_3/devops/local-sim}"

docker image inspect docker:cli >/dev/null 2>&1 || docker pull -q docker:cli

exec docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$HOST_DIR:$HOST_DIR" \
    -w "$HOST_DIR" \
    docker:cli docker compose -p dsa-sim "$@"
