#!/usr/bin/env bash

. ./venv/bin/activate

pip install girder girder_jobs
pip install -e ./lib/girder_worker
pip install -e ./lib/girder_worker/girder_worker/singularity
pip install -e ./lib/girder_worker/girder_worker/slurm
pip install -e ./lib/slicer_cli_web
pip install -e ./lib/slicer_cli_web/slicer_cli_web/singularity

# PATH="$HOME/misc/girder_worker/env/bin:$PATH" GW_DIRECT_PATHS=true python -m girder_worker -l info -Ofair --prefetch-multiplier=1 --without-heartbeat --concurrency=2
SIF_IMAGE_PATH=~/work/digital_slide_archive/devops/slurm/SIF \
LOGS=~/work/digital_slide_archive/devops/slurm/logs \
GIRDER_WORKER_SLURM_SUBMIT_SCRIPT=~/work/digital_slide_archive/devops/slurm/worker/lib/girder_worker/girder_worker/slurm/girder_worker_slurm/singluarity.slurm \
GW_DIRECT_PATHS=true \
python -m girder_worker -l info -Ofair --prefetch-multiplier=1 --without-heartbeat --concurrency=2
