# Local slurm + apptainer simulation (Girder 3)

This is a self-contained local simulation of the DSA slurm/apptainer
deployment described in `../slurm` (see also `../slurm/HPC.md` for the
background on HPC deployments).  It runs entirely in docker containers on a
single machine:

- `mongodb`, `rabbitmq`, `memcached` — standard DSA services.
- `girder` — built from `../../apptainer.Dockerfile` (`dsa_common` with
  apptainer installed), privileged so that apptainer works inside the
  container.  Provisioning replaces the stock `girder_worker` and
  `slicer_cli_web` with the `slurm` branch of girder_worker and the
  `slicer-cli-web-singularity` branch of slicer_cli_web, and pulls
  `dsarchive/histomicstk:latest` into a SIF under `./SIF/`.
- `worker` — a `dsa_common` + apptainer image with the slurm client tools and
  munge added (`worker.Dockerfile`).  It runs `girder_worker` with the
  singularity and slurm plugins, submitting jobs with `sbatch`.
- `slurm` — a single-node slurm "cluster" (munge + slurmctld + slurmd in one
  container, also with apptainer).  It plays the role of an HPC compute node:
  slurm jobs run `apptainer exec` on the shared SIF files.

The directories `./assetstore`, `./SIF`, `./tmp`, and `./logs` are bind
mounted into the girder, worker, and slurm containers, mirroring the shared
filesystem requirement of an HPC deployment.

## Requirements

- docker with support for privileged containers and `/dev/fuse` (verified
  working in the development environment).
- The docker daemon resolves bind-mount sources on the host filesystem, but
  this environment runs inside a container whose repository is not visible to
  the host.  Therefore the compose project is **deployed** to a host-visible
  directory and run from there:

  ```bash
  ./deploy.sh [--reset]   # copy this directory to the host (DSA_SIM_HOST_DIR,
                          # default /home/ubuntu/dsa_3/devops/local-sim);
                          # --reset wipes the deployed copy, including the
                          # database and assetstore.
  ./compose.sh up -d      # run compose via a helper container (the project
                          # directory must be bind-mounted at its host path,
                          # since compose records bind sources relative to the
                          # project directory as it sees them).
  ```

  A shared munge key is generated in `./munge/munge.key` on first deploy.

## Usage

Once the stack is up (girder may take several minutes to provision, clone the
plugin branches, and pull the histomicstk SIF):

- Girder: http://localhost:8081 (login `admin` / `password`).
- The `Tasks` collection holds the slicer_cli_web task items registered from
  the SIF (the singularity plugin stores them under a `Docker Hub` folder
  rather than the configured task folder).
- Jobs can be run from HistomicsUI or with
  `POST /api/v1/slicer_cli_web/cli/<cliId>/run`, passing input item/file ids
  and `<param>_folder` for outputs.
- Slurm jobs are visible with `docker exec dsa-sim-slurm-1 squeue`; job logs
  are written to `./logs/<uuid>logs.log`.

## Notable configuration

- `GIRDER_WORKER_SLURM_MOUNT_PREFIX` must be set on the worker (empty string
  is fine when the assetstore path is identical on the "compute node"), or
  path mapping in `girder_worker_slurm` fails with a TypeError.
- `provision.py` requires `pyaml` and `setuptools<81` (newer setuptools no
  longer ships `pkg_resources`).
- RabbitMQ needs `deprecated_features.permit.transient_nonexcl_queues = true`
  (`./rabbitmq.conf`) for the celery version used by girder_worker.
- The worker runs as root (`C_FORCE_ROOT=1`) since apptainer inside the
  container requires it.
- The `slurm` partition is named `girdercompute`, as hardcoded in
  `girder_worker_slurm/singularity.slurm`.

## Differences from a real HPC deployment

- Everything runs on one machine; there is no real multi-node scheduler, and
  the worker submits jobs to a single-node cluster instead of a login node.
- Containers run privileged with apptainer installed inside; on HPC, apptainer
  would be provided by the cluster.
- The slurm "cluster" has no accounting/associations (`accounting_storage/none`,
  `priority/basic`), so any user may submit.
- The girder and worker containers run as root rather than a mapped
  `DSA_USER`, so files under `./assetstore`, `./logs`, etc. are owned by root.

## Status / next steps

- Verified end to end: provisioning, SIF pull, task registration, job
  submission via sbatch, apptainer execution on the "compute node", and output
  annotation upload back to girder.

## Girder 5 (dsa_common_5) status

A Girder 5 variant of this simulation exists in `../local-sim-5`.  It uses
the opt-in apptainer/slurm job execution support ported into the girder 5
tree (the girder `apptainer-port` branch), enabled with the
`slicer_cli_web.singularity_enabled` setting and
`GIRDER_WORKER_SINGULARITY_ENABLED`, and is verified end to end the same way
as this simulation.  Until the port is merged, its images overlay the ported
subtrees onto the stock `dsa_common_5` tree; see the TODO comments in its
Dockerfiles and `deploy.sh`.
