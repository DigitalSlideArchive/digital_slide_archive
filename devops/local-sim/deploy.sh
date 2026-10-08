#!/bin/bash
# Deploy the local-sim configuration to a host-visible directory.
#
# The docker daemon is shared with the host, so bind-mount sources are
# resolved on the host filesystem, not inside this container.  This script
# copies the compose project (excluding runtime data and the lib/ reference
# clones) to the host so that bind mounts work.
#
# With --reset, the target directory is wiped first (including the database
# and assetstore), giving a clean provisioning run.
set -euo pipefail
cd "$(dirname "$0")"

HOST_DIR="${DSA_SIM_HOST_DIR:-/home/ubuntu/dsa_3/devops/local-sim}"

# alpine is only used as a file-moving helper.
docker image inspect alpine:latest >/dev/null 2>&1 || docker pull -q alpine:latest

# Generate the shared munge key if it does not exist yet (used by the slurm
# node and the worker to authenticate with each other).  NOTE: this must be a
# plain file write in the repository, not a docker bind-mount (bind sources
# resolve on the host, which would silently regenerate the key in the
# deployed copy on every deploy).
if [[ ! -f munge/munge.key ]]; then
    mkdir -p munge
    dd if=/dev/urandom of=munge/munge.key bs=1024 count=1
fi

if [[ "${1:-}" == "--reset" ]]; then
    docker run --rm -v "$HOST_DIR:/dest" alpine \
        sh -c 'rm -rf /dest/* /dest/.[!.]* 2>/dev/null; true'
fi

tar -C . --exclude=./lib -cf - . |
    docker run --rm -i -v "$HOST_DIR:/dest" alpine tar -xf - -C /dest

echo "Deployed to host directory: $HOST_DIR"
