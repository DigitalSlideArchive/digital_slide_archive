#!/usr/bin/env bash

singularity pull SIF/rabbitMQ.sif library://sylabs/examples/rabbitmq
singularity pull SIF/mongodb.sif docker://mongo:latest
singularity pull SIF/memcached.sif docker://memcached:latest
