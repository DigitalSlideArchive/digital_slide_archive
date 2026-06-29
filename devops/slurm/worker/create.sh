#!/usr/bin/env bash

rm -rf ./lib/girder_worker ./lib/slicer_cli_web ./venv

python -m venv ./venv

git clone --branch slurm https://github.com/girder/girder_worker.git ./lib/girder_worker
git clone --branch slicer-cli-web-singularity https://github.com/willdunklin/slicer_cli_web.git ./lib/slicer_cli_web
