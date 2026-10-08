# Local slurm + apptainer simulation (Girder 5)

This is a self-contained local simulation of the DSA slurm/apptainer
deployment described in `../slurm` (see also `../slurm/HPC.md`), built on the
Girder 5 stack (`dsa_common_5`).  It mirrors `../local-sim` (the Girder 3
variant) and runs entirely in docker containers on a single machine:

- `mongodb`, `rabbitmq`, `redis` — standard DSA services (redis replaces the
  memcached service of the Girder 3 stack; it backs girder notifications and
  the large_image cache).
- `girder` — built from `apptainer.Dockerfile` (`dsa_common_5` with apptainer
  installed and the opt-in apptainer/slurm job execution port from the girder
  `apptainer-port` branch overlaid on the stock tree), privileged so that
  apptainer works inside the container.  The singularity flow is enabled with
  the `slicer_cli_web.singularity_enabled` girder setting, so provisioning
  pulls `dsarchive/histomicstk:latest` as a SIF into `./SIF/` and registers
  its CLI tasks.
- `worker` — the same image with the slurm client tools and munge added
  (`worker.Dockerfile`).  It runs `girder_worker` with the singularity and
  slurm task paths enabled (`GIRDER_WORKER_SINGULARITY_ENABLED` and
  `GIRDER_WORKER_SLURM_SUBMIT_SCRIPT`), submitting jobs with `sbatch`.
- `slurm` — a single-node slurm "cluster" (munge + slurmctld + slurmd in one
  container, also with apptainer).  It plays the role of an HPC compute node:
  slurm jobs run `apptainer exec` on the shared SIF files.

The directories `./assetstore`, `./SIF`, `./tmp`, and `./logs` are bind
mounted into the girder, worker, and slurm containers, mirroring the shared
filesystem requirement of an HPC deployment.

## Requirements

- docker with support for privileged containers and `/dev/fuse`.
- The docker daemon resolves bind-mount sources on the host filesystem, but
  this environment runs inside a container whose repository is not visible to
  the host.  Therefore the compose project is **deployed** to a host-visible
  directory and run from there, and the image build contexts are
  self-contained inside this directory (the girder repository is not used as
  a build context):

  ```bash
  ./deploy.sh [--reset]   # extract the port overlay from a local girder
                          # checkout, then copy this directory to the host
                          # (DSA_SIM_HOST_DIR, default
                          # /home/ubuntu/dsa_3/devops/local-sim-5);
                          # --reset wipes the deployed copy, including the
                          # database and assetstore.
  ./compose.sh build girder worker slurm
  ./compose.sh up -d      # run compose via a helper container (the project
                          # directory must be bind-mounted at its host path,
                          # since compose records bind sources relative to the
                          # project directory as it sees it).
  ```

  A shared munge key is generated in `./munge/munge.key` on first deploy.

  The port overlay is extracted by `deploy.sh` from a local girder checkout
  (`DSA_SIM_GIRDER_REPO`, default `/home/ubuntu/girder`, ref
  `DSA_SIM_GIRDER_REF`, default `apptainer-port`) into `./girder-overlay/`.
  TODO: once the apptainer/slurm port is merged into the girder repository
  and `dsa5.Dockerfile` builds from a ref that contains it, remove the
  overlay from `apptainer.Dockerfile` and `worker.Dockerfile` and the
  extraction step from `deploy.sh`.

## Usage

Once the stack is up (girder takes several minutes to provision and pull the
histomicstk SIF into `./SIF/`):

- Girder: http://localhost:8082 (login `admin` / `password`).
- The `Tasks` collection holds the slicer_cli_web task items registered from
  the SIF.
- Jobs can be run from HistomicsUI or with
  `POST /api/v1/slicer_cli_web/cli/<cliId>/run`, passing each input parameter
  as a girder file id and each output as `<param>=<filename>` plus
  `<param>_folder=<folderId>`.  Output file items are created in the
  requested folder (e.g., a BackgroundIntensity run creates an
  `intensity.anot` item containing the computed values).
- Slurm jobs are visible with `docker exec dsa-sim5-slurm-1 squeue`; job logs
  are written to `./logs/<uuid>logs.log` (this is the
  `GIRDER_WORKER_SINGULARITY_LOGS_DIR`).

## Verification

Verified end to end with a fresh `./deploy.sh --reset`:

- provisioning pulls the histomicstk SIF (`dsarchive_histomicstk_latest.sif`,
  ~940 MB) into `SIF_IMAGE_PATH` and registers 9 histomicstk CLIs via the
  singularity ingest flow;
- a `BackgroundIntensity` run on a small uploaded PNG: the worker generated
  the apptainer command, submitted it with `sbatch` to the `girdercompute`
  partition, the slurm node executed `apptainer exec` on the shared SIF, the
  job state went to COMPLETED (exit 0), the girder job status went to
  SUCCESS, and the `.anot` output was uploaded back into girder;
- zero errors in the worker log.

## Notable configuration

- `GIRDER_WORKER_SINGULARITY_ENABLED` gates the singularity task registration
  on the worker; without it the worker behaves exactly like stock
  girder-worker (docker only).  The server side is gated by the
  `slicer_cli_web.singularity_enabled` setting, seeded here via both
  `provision.yaml` and the `GIRDER_SETTING_SLICER_CLI_WEB_SINGULARITY_ENABLED`
  environment variable.
- `SIF_IMAGE_PATH` (`/SIF`), `GIRDER_WORKER_SINGULARITY_LOGS_DIR` (`/logs`),
  and `GIRDER_WORKER_SLURM_SUBMIT_SCRIPT` (the in-tree
  `singularity.slurm` template) must be set on the worker;
  `GIRDER_WORKER_SLURM_MOUNT_PREFIX` must be empty or unset in this
  simulation since the assetstore path is identical on the "compute node".
- The worker celery broker/backend are set through `CELERY_BROKER_URL` /
  `CELERY_RESULT_BACKEND` and the girder-worker equivalents
  (`GIRDER_WORKER_BROKER` / `GIRDER_WORKER_BACKEND`); there is no
  `worker.local.cfg` in this simulation.
- The worker runs as root (`C_FORCE_ROOT=1`) since apptainer inside the
  container requires it.
- The slurm partition is named `girdercompute` (hardcoded in the submit
  script template; `slurm.conf` defines it).
- RabbitMQ needs `deprecated_features.permit.transient_nonexcl_queues = true`
  (`./rabbitmq.conf`) for the celery version used by girder-worker.
- The slurm client and cluster must run matching protocol versions; both use
  the ubuntu 26.04 slurm packages (`worker.Dockerfile` and
  `slurm/Dockerfile`), so this holds.

## Differences from the Girder 3 simulation (../local-sim)

- `redis` replaces `memcached`; girder and the worker are configured through
  environment variables instead of `/etc/girder.cfg` and `worker.cfg`.
- The apptainer/slurm code comes from the in-tree girder port behind opt-in
  flags, rather than from separately cloned plugin branches installed during
  provisioning; there are no git clones or fork installs in `provision.yaml`.
- Girder listens on port 8082 (the Girder 3 sim uses 8081; the reference
  stacks use 8085/8087).
- Output files (such as the `.anot` annotation) are stored as items in the
  requested output folder rather than attached to the input item.

## Differences from a real HPC deployment

- Everything runs on one machine; there is no real multi-node scheduler, and
  the worker submits jobs to a single-node cluster instead of a login node.
- Containers run privileged with apptainer installed inside; on HPC, apptainer
  would be provided by the cluster.
- The slurm "cluster" has no accounting/associations (`accounting_storage/none`,
  `priority/basic`), so any user may submit.
- The girder and worker containers run as root rather than a mapped
  `DSA_USER`, so files under `./assetstore`, `./logs`, etc. are owned by root.
