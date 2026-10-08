# PLAN.md: Local apptainer/slurm simulation for Girder 5

## Context

`devops/local-sim/` contains a working, verified local simulation of the
**Girder 3** slurm/apptainer deployment (see its README).  A Girder 5 variant
was attempted before the plugin support existed and was removed; the missing
pieces are documented in `devops/local-sim/README.md` ("Girder 5 status") and
require changes in the **girder repository** first — see `/home/ubuntu/girder/PLAN.md`
(the up-port of `girder_worker` singularity/slurm subpackages and the
`slicer_cli_web` singularity support, behind an opt-in feature flag).

This plan covers what to do **in this repository** once that girder work is
merged: build `devops/local-sim-5/`, verify it end to end, and update the
Girder 5 reference environments.

## Prerequisites

- girder with the ported feature (worker subpackages +
  `slicer_cli_web` singularity support, flag-gated).  NOTE: `dsa5.Dockerfile`
  builds `dsa_common_5` from a girder checkout with
  `git checkout v4-integration || true`, so confirm the branch/ref the image
  actually builds from contains the port; see `/home/ubuntu/girder/PLAN.md`.
- The environment must allow privileged docker containers and `/dev/fuse`
  (verified in this sandbox).
- `docker compose` (plugin) available; in the restricted container the
  harness installs it into `~/.docker/cli-plugins` if missing.

## What is reusable as-is from `devops/local-sim`

- `slurm/` (slurm node image: munge + slurmctld + slurmd + apptainer,
  `slurm.conf`, `cgroup.conf`, `slurmnode.sh`) — copy verbatim.
- `deploy.sh` / `compose.sh` (the host-path indirection required by this
  sandbox: the docker daemon resolves bind sources on the host, and the
  repository is not visible to it; the project is copied to a host-visible
  directory and compose runs in a helper container with the project mounted
  **at its host path**).
- `worker.cfg` / `worker.dist.cfg` (celery config),
  `rabbitmq.conf` / `rabbitmq.advanced.config` (RabbitMQ 4 deprecated-feature
  permit), `.gitignore` layout, munge-key generation.

## Step 1: create `devops/local-sim-5/`

Files (mirroring `devops/local-sim/`):

```
devops/local-sim-5/
  apptainer.Dockerfile      # FROM dsarchive/dsa_common_5 + apptainer-suid
  worker.Dockerfile         # FROM dsa_common_apptainer:g5 + slurm-client + munge
  docker-compose.yml
  deploy.sh / compose.sh    # DSA_SIM_PROJECT=dsa-sim5, host dir local-sim-5
  provision.py              # copy from ../ver5
  provision.yaml            # adapted, see below
  start_girder.sh           # adapted from ../ver5/start_girder.sh (root mode)
  start_worker_slurm.sh     # munged + provision + celery, girder-5 paths
  worker.cfg / worker.dist.cfg
  rabbitmq.conf / rabbitmq.advanced.config  # copies from ../ver5
  slurm/                    # copy from ../local-sim/slurm
  .gitignore, README.md
```

Girder 5 differences from the Girder 3 sim:

- **Services:** `redis` replaces `memcached` (notifications and the
  large_image cache); girder is configured through environment variables
  (`GIRDER_MONGO_URI`, `CELERY_BROKER_URL`, `GIRDER_NOTIFICATION_REDIS_URL`,
  `LARGE_IMAGE_CACHE_*`, ...) rather than `/etc/girder.cfg`.
- **Image:** `apptainer.Dockerfile` is `FROM dsarchive/dsa_common_5` plus
  `software-properties-common`, the `apptainer/ppa` PPA, and
  `apptainer-suid` (base is Ubuntu 26.04; the PPA works there).
- **Paths:** the girder source tree lives at `/opt/girder` in the image
  (worker at `/opt/girder/worker`, slicer_cli_web at
  `/opt/girder/plugins/slicer_cli_web`); the slurm submit script is at
  `/opt/girder/worker/girder_worker/slurm/girder_worker_slurm/singularity.slurm`.
- **Ports:** expose girder on 8082 (8081 is the Girder 3 sim; the reference
  stacks use 8085/8087).

`provision.yaml` (much simpler than the Girder 3 one — no git clones, no
forks):

```yaml
settings:
  worker.api_url: "http://girder:8080/api/v1"
  worker.direct_path: True
  slicer_cli_web.task_folder: "resourceid:collection/Tasks/Slicer CLI Web Tasks"
  # new feature flag (or set via env GIRDER_SETTING_...):
  slicer_cli_web.singularity_enabled: True
worker-config: /opt/girder/worker/girder_worker/worker.local.cfg
worker:
  config: /opt/girder/worker/girder_worker/worker.local.cfg
  shell:
    - pip install --force-reinstall -e "/opt/girder/worker[singularity,slurm]"
    - cp /opt/worker.cfg /opt/girder/worker/girder_worker/worker.local.cfg
shell:
  - pip install --force-reinstall -e "/opt/girder[slicer-cli-web-singularity]"
```

(Adjust the extras names to whatever the girder port actually ships; if the
packages are in-tree at `/opt/girder`, plain editable installs of the
subpackages with `--no-deps` also work — that is what the
`../singularity-5/provision.yaml` shell steps do.)

Worker environment (compose):

```
GIRDER_WORKER_SINGULARITY_ENABLED: "1"
SIF_IMAGE_PATH: /SIF
LOGS: /logs
TMP: /tmp
TMPDIR: /tmp
GW_DIRECT_PATHS: "true"
C_FORCE_ROOT: "1"
GIRDER_WORKER_SLURM_SUBMIT_SCRIPT: /opt/girder/worker/girder_worker/slurm/girder_worker_slurm/singularity.slurm
GIRDER_WORKER_SLURM_MOUNT_PREFIX: ""   # must be set (may be empty)
```

Girder environment: the flag setting (e.g.
`GIRDER_SETTING_SLICER_CLI_WEB_SINGULARITY_ENABLED: "true"`, if the setting
supports env seeding in girder 5) plus the standard `ver5` variable set.

## Step 2: verify end to end

1. `./deploy.sh --reset && ./compose.sh build girder worker && ./compose.sh up -d`
2. Wait for provisioning (SIF pull of `dsarchive/histomicstk:latest` into
   `./SIF/`, CLI task registration).
3. Upload a small test image (PNG is fine; girder two-phase upload:
   `POST /file?...&size=N` with the bytes in the body).
4. `POST /api/v1/slicer_cli_web/cli/<cliId>/run` with
   `slide_path=<fileId>` plus each output param and its `<param>_folder`.
5. Expect: `sbatch` submission visible in the slurm container
   (`squeue`), the CLI executed via `apptainer exec` on the SIF, job status
   SUCCESS, and the output annotation saved on the input item.
6. Zero errors in the worker log; the job log (in `./logs/`) shows the
   apptainer invocation.

Use the verified Girder 3 flow as the reference script (see the transcript
in the local-sim README and this repo's git history around the
`local-sim` commit).

## Step 3: update the reference environments

- `devops/ver5/`: add an optional compose override or a
  `docker-compose.singularity.yml` that mounts the shared dirs
  (`SIF`, `tmp`), sets the feature-flag environment on girder and worker,
  and uses apptainer-enabled image builds — the Girder 5 analogue of
  `devops/slurm/docker-compose.yml`.
- `devops/slurm/HPC.md`: update "For Apptainer job execution using Slurm" to
  note that girder 5 supports this behind the flag; the current text implies
  Girder 3 only.
- `devops/singularity-5/`: once the girder-side plugins are in-tree, the
  `/src/girder` checkout and the `--force-reinstall` shell steps can be
  replaced by the stock image plus the flag; refresh its README.
- `devops/local-sim/README.md`: remove/replace the "Girder 5 status" gap
  section with a pointer to `../local-sim-5`.

## Notes and gotchas carried over from the Girder 3 simulation

- Bind-mount sources resolve on the docker **host**, not inside the agent
  container; `deploy.sh` + `compose.sh` handle this (project must be mounted
  at its host path inside the compose helper, or the recorded bind sources
  point at a nonexistent path).
- `GIRDER_WORKER_SLURM_MOUNT_PREFIX` must be present (may be empty) or the
  slurm path mapping fails; the girder port should fix this, but keep the
  variable set in the sim anyway.
- The slurm submit template requires a partition named `girdercompute`
  (`slurm.conf` defines it).
- The single-node slurm container needs `cgroup.conf`
  (`IgnoreSystemd=yes`), `accounting_storage/none`, `priority/basic`, and a
  writable cgroupfs (`mkdir -p /sys/fs/cgroup/system.slice` in the node
  entrypoint) — all already encoded in `../local-sim/slurm/`.
- The slurm client and cluster must run matching protocol versions
  (mismatches surface as opaque munge authentication errors).
- Provisioning needs `pyaml` and (girder 3 only) `setuptools<81`;
  `dsa_common_5` is Python 3.13 — check whether the girder-5 provisioner
  still imports `pkg_resources` before assuming the pin is needed (the
  `ver5` provision.py does not import it).
- Worker runs as root in the sim (apptainer in a privileged container);
  `C_FORCE_ROOT=1` is required by celery.
- Everything created on the shared daemon must be namespaced (`dsa-sim5`
  compose project) — the daemon also runs the real reference stacks.
