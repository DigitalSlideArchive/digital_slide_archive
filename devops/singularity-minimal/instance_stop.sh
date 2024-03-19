#!/usr/bin/env bash

singularity instance stop test-dsarchive

find ./opt/* -not -path "*opt/local_*" -not -path "*opt/.gitignore" -delete
