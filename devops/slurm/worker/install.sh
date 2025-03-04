#!/usr/bin/env bash

. ./venv/bin/activate

pip install girder girder_jobs
pip install -e ./lib/girder_worker
pip install -e ./lib/girder_worker/girder_worker/singularity
pip install -e ./lib/girder_worker/girder_worker/slurm
pip install -e ./lib/slicer_cli_web
pip install -e ./lib/slicer_cli_web/slicer_cli_web/singularity
