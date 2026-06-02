#!/usr/bin/env bash
set -euxo pipefail

cd "$(dirname "$0")"
GIRDER_SRC="${GIRDER_SRC:-$(realpath ../../../girder)}"
if [ ! -d "$GIRDER_SRC" ]; then
    echo "Missing GIRDER_SRC directory: $GIRDER_SRC"
    exit 1
fi

apptainer instance stop -a || echo "No instances stopped"

# Load Modules
# module load slurm-drmaa

# Start instances
# MongoDB, RabbitMQ, Redis
apptainer instance start \
    --bind ./db:/data/db \
    SIF/mongodb.sif dsa-mongodb-1

apptainer instance start \
    --env RABBITMQ_DEFAULT_USER=guest \
    --env RABBITMQ_DEFAULT_PASS=guest \
    --bind ./rabbitmqdata:/var/lib/rabbitmq/ \
    SIF/rabbitMQ.sif dsa-rabbitMQ-1

apptainer instance start SIF/redis.sif dsa-redis-1

# # clean girder opt
# find ./opt/* -not -path "*opt/local_*" -not -path "*opt/.gitignore" -delete

# # set up worker opt
# # rm -rf ./worker_opt/*
# # cp -r ./opt/* ./worker_opt/
rm -rf ./tmp/*
mkdir -p ./tmp/sifs
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
    --bind ../ver5/provision.py:/opt/provision.py \
    --bind "$GIRDER_SRC":/src/girder \
    --bind $TMP_OPT_GIRDER:/opt \
    SIF/dsa_common.sif test-dsarchive

apptainer instance start \
    --bind ./logs:/logs \
    --bind ./start_worker.sh:/opt/start_worker.sh \
    --bind ./provision.yaml:/opt/provision.yaml \
    --bind ../ver5/provision.py:/opt/provision.py \
    --bind "$GIRDER_SRC":/src/girder \
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
    --env SIF_IMAGE_PATH="$(pwd)/tmp/sifs/" \
    --env TMPDIR="$(pwd)/tmp" \
    --env LOGS="$(pwd)/logs" \
    --env DSA_PROVISION_YAML=/opt/provision.yaml \
    --env GIRDER_WORKER_BROKER=amqp://guest:guest@localhost:5672/ \
    --env GIRDER_WORKER_BACKEND=rpc://guest:guest@localhost:5672/  \
    --env CELERY_BROKER_URL=amqp://guest:guest@localhost:5672/ \
    --env CELERY_RESULT_BACKEND=rpc://guest:guest@localhost:5672/ \
    instance://dsa-worker-1 /opt/start_worker.sh &

    # --env PATH=/opt/slurm/bin:$PATH \
    # --env SLURM_QOS=pinaki.sarder-dsa \
    # --env SLURM_ACCOUNT=pinaki.sarder-dsa \


sleep 30

apptainer run \
    --env SIF_IMAGE_PATH="$(pwd)/tmp/sifs/" \
    --env TMPDIR="$(pwd)/tmp" \
    --env LOGS="$(pwd)/logs" \
    --env DSA_PROVISION_YAML=/opt/provision.yaml \
    --env CELERY_BROKER_URL=amqp://guest:guest@localhost:5672/ \
    --env CELERY_RESULT_BACKEND=rpc://guest:guest@localhost:5672/ \
    --env GIRDER_NOTIFICATION_REDIS_URL=redis://localhost:6379 \
    --env LARGE_IMAGE_CACHE_BACKEND=redis \
    --env LARGE_IMAGE_CACHE_REDIS_URL=localhost:6379 \
    --env DSA_WORKER_API_URL=http://localhost:8080/api/v1 \
    instance://test-dsarchive /opt/start_girder.sh

    # --env PATH=/opt/slurm/bin:$PATH \
    # --env SLURM_QOS=pinaki.sarder-dsa \
    # --env SLURM_ACCOUNT=pinaki.sarder-dsa \
