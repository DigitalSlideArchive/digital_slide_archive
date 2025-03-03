#!/usr/bin/env bash

. ./venv/bin/activate

# TODO: communicate TMP assignment (it needs to be accessible by worker's node and compute node)

SIF_IMAGE_PATH=~/work/digital_slide_archive/devops/slurm/SIF \
    TMP=/slurmshare/test-dsa-slurm/tmp \
    LOGS=~/work/digital_slide_archive/devops/slurm/logs \
    GIRDER_WORKER_SLURM_SUBMIT_SCRIPT=~/work/digital_slide_archive/devops/slurm/worker/lib/girder_worker/girder_worker/slurm/girder_worker_slurm/singluarity.slurm \
    GW_DIRECT_PATHS=true \
    python -m girder_worker -l info -Ofair --prefetch-multiplier=1 --without-heartbeat --concurrency=2
