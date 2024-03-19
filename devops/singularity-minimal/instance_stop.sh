#!/usr/bin/env bash

singularity instance stop test-dsarchive

find ./opt/* -not -path "*opt/local_*" -not -name "hist.sif" -delete
