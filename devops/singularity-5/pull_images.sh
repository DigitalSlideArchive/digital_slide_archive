#!/usr/bin/env bash

apptainer pull SIF/rabbitMQ.sif library://sylabs/examples/rabbitmq
apptainer pull SIF/mongodb.sif docker://mongo:latest
apptainer pull SIF/redis.sif docker://redis:latest
