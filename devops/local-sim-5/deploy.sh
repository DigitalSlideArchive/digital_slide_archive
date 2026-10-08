#!/bin/bash
# Deploy the local-sim-5 configuration to a host-visible directory.
#
# The docker daemon is shared with the host, so bind-mount sources are
# resolved on the host filesystem, not inside this container.  This script
# copies the compose project (excluding runtime data) to the host so that
# bind mounts work.
#
# This also extracts the apptainer/slurm port overlay (see
# apptainer.Dockerfile) from a local girder checkout into ./girder-overlay,
# which is part of the image build context.  TODO: remove this once the port
# is merged and dsa_common_5 is built from a ref that contains it.
#
# With --reset, the target directory is wiped first (including the database
# and assetstore), giving a clean provisioning run.
set -euo pipefail
cd "$(dirname "$0")"

HOST_DIR="${DSA_SIM_HOST_DIR:-/home/ubuntu/dsa_3/devops/local-sim-5}"
GIRDER_REPO="${DSA_SIM_GIRDER_REPO:-/home/ubuntu/girder}"
GIRDER_REF="${DSA_SIM_GIRDER_REF:-apptainer-port}"

if [[ ! -d "$GIRDER_REPO/.git" ]]; then
    echo "The girder repository was not found at $GIRDER_REPO" \
        "(override with DSA_SIM_GIRDER_REPO)." >&2
    exit 1
fi

mkdir -p girder-overlay
git -C "$GIRDER_REPO" archive "$GIRDER_REF" \
    worker/girder_worker/singularity \
    worker/girder_worker/slurm \
    worker/setup.py \
    plugins/slicer_cli_web/slicer_cli_web/singularity \
    plugins/slicer_cli_web/slicer_cli_web/config.py \
    plugins/slicer_cli_web/slicer_cli_web/docker_resource.py \
    plugins/slicer_cli_web/slicer_cli_web/image_job.py \
    plugins/slicer_cli_web/slicer_cli_web/rest_slicer_cli.py \
    plugins/slicer_cli_web/setup.py \
    | tar -x -C girder-overlay

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
