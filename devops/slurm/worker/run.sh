#!/usr/bin/env bash

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

. ./venv/bin/activate

echo -e "Before running, please edit environment variables per README.md instructions.\n Once set, remove this line from script.\n" && exit 1

# CHANGE THESE VALUES (see README.md)
TMP=/slurmshare/test-dsa-slurm/tmp \
    SIF_IMAGE_PATH="$CURRENT_DIR/../SIF" \
    LOGS="$CURRENT_DIR/../logs" \
    GIRDER_WORKER_SLURM_SUBMIT_SCRIPT="$CURRENT_DIR/lib/girder_worker/girder_worker/slurm/girder_worker_slurm/singluarity.slurm" \
    GW_DIRECT_PATHS=true \
    python -m girder_worker -l info -Ofair --prefetch-multiplier=1 --without-heartbeat --concurrency=2
