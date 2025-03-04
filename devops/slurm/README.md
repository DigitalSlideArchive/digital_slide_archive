# DSA Slurm

This is a setup for running the DSA with Slurm workers.

## Requirements

We expect to run on:

- Slurm control node (TODO: what's the proper name?)
  - Have access to `sbatch`, `scontrol show job`, `scancel`.
- Have apptainer installed on compute nodes (TODO: what's the proper name?)


## Key differences from typical DSA setup:

### RabbitMQ

Port 5672 is exposed.


### MongoDB

Port 27017 is exposed.


### Worker

We run the girder_worker outside of the docker containers. We do this because we need the worker to access the Slurm CLI.
The worker setup is located in `worker/`.

Key files in `worker/`:
- `create.sh` - creates a virtual environment and clones `girder_worker`/`slicer_cli_web` repositories.
- `install.sh` - installs the slurm worker from cloned repositories.
- `run.sh` - runs the girder worker. Contains environment variables THAT MUST BE CONFIGURED (see below).
- `lib/` - directory for cloned repositories (TODO: rename?)


*BEFORE RUNNING*: edit `run.sh` to ensure the correct environment variables set. See [Environment variables](#environment-variables) section for more information.


To get started with the worker, run the following commands:
```bash
cd worker
# only run create.sh when you first set up the worker
# (or when you want to recreate the virtual environment)
./create.sh

# run install.sh to editable install the girder_worker
# you should only need to run this once
./install.sh

# *set the environment variables in run.sh*

# run the worker
./run.sh
```

Navigate to http://{dsa.url}/#plugins/worker/task/status to check if the worker is connected to Girder.


You may need to modify the `Worker` plugin settings in Girder so the worker can find Girder. Ensure the `Alternative Girder API URL` setting is set to the Girder API URL from the perspective of the worker. In most cases, this will be `http://localhost:8080/api/v1`.

If the worker fails to connect to `rabbitmq`, this may be because the celery `broker`/`backend` configuration is invalid. To check these config values, see `worker/lib/girder_worker/girder_worker/worker.dist.cfg`. In most cases these values should look like `://guest:guest@localhost/`, where localhost is the RabbitMQ address (with the implied default port of 5672).


### Misc

*One RabbitMQ/Celery config note:*

While the worker expects RabbitMQ broker/backend to run on `localhost`, the girder docker container will expect the address to be `rabbitmq`.
To ensure girder gets the correct configuration, we mount the properly configured `./worker.dist.cfg` and copy it to the correct location during girder provisioning.


## Environment variables

The following specify values specify directories which need to be accessible by both the worker's node and compute nodes.
- `TMP`: temporary directory for the worker to store files.
- `LOGS`: directory for the worker to store logs.
- `SIF_IMAGE_PATH`: directory for the worker to store Singularity/Apptainer images. See note below.
- `GIRDER_WORKER_SLURM_SUBMIT_SCRIPT`: path to the script that submits jobs to Slurm. See `girder_worker/girder_worker/slurm/girder_worker_slurm/singularity.slurm`.


Additionally, `SIF_IMAGE_PATH` should be set to the same directory we mount in `docker-compose.yaml` for the girder container (whatever is mounted to `/SIF`).
This is because girder will pull the Singularity/Apptainer images and store them in this directory. The worker will then use this directory to access the images.

These environment variables are set in `worker/run.sh`. You must edit this file to set the correct values before running the worker.
