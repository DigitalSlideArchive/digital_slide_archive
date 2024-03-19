#!/usr/bin/env bash

# singularity instance start --bind ./db:/data/db SIF/mongodb.sif dsa-mongodb-1
# singularity instance start SIF/memcached.sif dsa-memcached-1
# singularity instance start SIF/rabbitMQ.sif dsa-rabbitMQ-1
singularity instance start \
    --bind ./opt:/opt \
    --bind ./assetstore:/assetstore \
    --bind ./logs:/logs \
    --bind ./fuse:/fuse \
    --bind ./girder.cfg:/etc/girder.cfg \
    --bind ./start_girder.sh:/opt/start_girder.sh \
    --bind ./provision.yaml:/opt/provision.yaml \
    SIF/dsa_common.sif test-dsarchive

# needed to use singularity in singularity (for `singularity pull`, etc)
    # --bind /usr/bin/singularity:/usr/bin/singularity \
    # --bind /usr/bin/apptainer:/usr/bin/apptainer \
    # --bind /etc/apptainer/apptainer.conf:/etc/apptainer/apptainer.conf \
    # --bind /usr/bin/mksquashfs:/usr/bin/mksquashfs \
    # --bind /usr/bin/unsquashfs:/usr/bin/unsquashfs \
    # --bind /usr/lib/x86_64-linux-gnu/liblzo2.so.2:/usr/lib/x86_64-linux-gnu/liblzo2.so.2 \

# needed to run `singularity exec` (doesn't work because of permissions)
    # --bind /etc/apptainer:/etc/apptainer \
    # --bind /var/lib/apptainer/mnt/session:/var/lib/apptainer/mnt/session \
    # --bind /usr/libexec/apptainer:/usr/libexec/apptainer \
    # --bind /usr/libexec/apptainer/bin/starter:/usr/libexec/apptainer/bin/starter \
    # --bind /etc/apptainer/capability.json:/etc/apptainer/capability.json \
