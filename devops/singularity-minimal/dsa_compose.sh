#!/usr/bin/env bash
set -x

cd $(dirname $0)

apptainer instance stop -a || echo "No instances stopped"

# Load Modules
# module load slurm-drmaa

# Add / Pull images if not pulled
# Start instances
## Start MongoDB and RabbitMQ
apptainer instance start \
    --bind ./db:/data/db \
    SIF/mongodb.sif dsa-mongodb-1

apptainer instance start \
    --env RABBITMQ_DEFAULT_USER=guest \
    --env RABBITMQ_DEFAULT_PASS=guest \
    --bind ./rabbitmqdata:/var/lib/rabbitmq/ \
    SIF/rabbitMQ.sif dsa-rabbitMQ-1

apptainer instance start SIF/memcached.sif dsa-memcached-1

# # clean girder opt
# find ./opt/* -not -path "*opt/local_*" -not -path "*opt/.gitignore" -delete

# # set up worker opt
# # rm -rf ./worker_opt/*
# # cp -r ./opt/* ./worker_opt/
rm -rf ./tmp/*
TMP_OPT_GIRDER=$(mktemp -d --tmpdir=./tmp)
TMP_OPT_WORKER=$(mktemp -d --tmpdir=./tmp)

## Start Girder and Worker
apptainer instance start \
    --bind ./assetstore:/assetstore \
    --bind ./logs:/logs \
    --bind ./tmp:/tmp \
    --bind ./fuse:/fuse \
    --bind ./girder.cfg:/etc/girder.cfg \
    --bind ./start_girder.sh:/opt/start_girder.sh \
    --bind ./provision.yaml:/opt/provision.yaml \
    --bind ../dsa/provision.py:/opt/provision.py \
    --bind $TMP_OPT_GIRDER:/opt \
    SIF/dsa_common.sif test-dsarchive
    # --bind ./opt:/opt \

    # --bind ./blue:/blue/pinaki.sarder/rc-svc-pinaki.sarder-web \
    # --no-mount /cmsuf \
    # --bind /blue/pinaki.sarder/rc-svc-pinaki.sarder-web/assetstore:/assetstore \
    # --bind /blue/pinaki.sarder/rc-svc-pinaki.sarder-web/logs:/logs \
    # --bind /blue/pinaki.sarder/rc-svc-pinaki.sarder-web/tmp:/tmp \
    # --bind /opt/slurm \
    # --bind /apps \
    # --bind /var/run/munge:/run/munge \

apptainer instance start \
    --bind ./logs:/logs \
    --bind ./start_worker.sh:/opt/start_worker.sh \
    --bind ./provision.yaml:/opt/provision.yaml \
    --bind ../dsa/provision.py:/opt/provision.py \
    --bind $TMP_OPT_WORKER:/opt \
    SIF/dsa_common.sif dsa-worker-1
    # --bind ./worker_opt:/opt \

    # --bind ./blue:/blue/pinaki.sarder/rc-svc-pinaki.sarder-web \
    # --no-mount /cmsuf \
    # --bind /blue/pinaki.sarder/rc-svc-pinaki.sarder-web/logs:/logs \
    # --bind /apps \
    # --bind /var/run/munge:/run/munge \
    # --bind /opt/slurm \

## Execute shells
apptainer exec instance://dsa-mongodb-1 mongod > /dev/null &

sleep 5 # TODO: WHY THE HELL IS THERE A RACE CONDITIONNNNNN
        # the files seem to be not mounted properly before this stuff runs

apptainer run \
    --env SIF_IMAGE_PATH="/home/local/KHQ/will.dunklin/work/digital_slide_archive/devops/singularity-minimal/tmp/sifs/" \
    --env TMPDIR=/home/local/KHQ/will.dunklin/work/digital_slide_archive/devops/singularity-minimal/tmp \
    --env LOGS=/home/local/KHQ/will.dunklin/work/digital_slide_archive/devops/singularity-minimal/logs \
    --env DSA_PROVISION_YAML=/opt/provision.yaml \
    --env GIRDER_WORKER_BROKER=amqp://guest:guest@localhost:5672/ \
    --env GIRDER_WORKER_BACKEND=rpc://guest:guest@localhost:5672/  \
    instance://dsa-worker-1 /opt/start_worker.sh &

    # --env PATH=/opt/slurm/bin:$PATH \
    # --env SLURM_QOS=pinaki.sarder-dsa \
    # --env SLURM_ACCOUNT=pinaki.sarder-dsa \


sleep 30

apptainer run \
    --env SIF_IMAGE_PATH="/home/local/KHQ/will.dunklin/work/digital_slide_archive/devops/singularity-minimal/tmp/sifs/" \
    --env TMPDIR=/home/local/KHQ/will.dunklin/work/digital_slide_archive/devops/singularity-minimal/tmp \
    --env LOGS=/home/local/KHQ/will.dunklin/work/digital_slide_archive/devops/singularity-minimal/logs \
    --env GIRDER_SETTING_WORKER_API_URL=http://0.0.0.0:8101/api/v1 \
    instance://test-dsarchive bash # /opt/start_girder.sh

    # --env PATH=/opt/slurm/bin:$PATH \
    # --env SLURM_QOS=pinaki.sarder-dsa \
    # --env SLURM_ACCOUNT=pinaki.sarder-dsa \
