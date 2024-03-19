#!/usr/bin/env bash

# singularity run instance://dsa-mongodb-1 &
# singularity run instance://dsa-memcached-1 &
# singularity run instance://dsa-rabbitMQ-1 &
# singularity run instance://dsa-dsarchive-1 bash -c 'python /opt/digital_slide_archive/devops/dsa/provision.py --sample-data && girder serve' &

# docker run --rm -it -p 27017:27017 mongo:latest mongod # needs to have port bound externally

singularity run instance://test-dsarchive
