# HPC and DSA

Most HPC environments disallow Docker execution. This document goes over the uses of Docker in the DSA and how to replace them with HPC-friendly alternatives.


## DSA using Docker

Let's go over the typical use cases of Docker in the DSA.

### Deployment

Docker is used in several contexts in the DSA. Firstly, the DSA is typically deployed using a `docker compose` [here](https://github.com/DigitalSlideArchive/digital_slide_archive/tree/master/devops/dsa), which launches the Girder app, worker, etc. The other main use of Docker is with the execution of `slicer_cli_web` jobs (i.e. jobs submitted through HistomicsUI, etc.), where a each job executes Docker container ran by the `girder_worker`. In this context, Docker is easily replacable since its only used to orchestrate processes.

To address the first case, to replace Docker in the DSA deployment the recommended option is to use Podman. Several research partners (namely Tulane and Pitt) have deployments executed using Podman as a drop in replacement for Docker. Podman configuration is required (TODO: add known details).

There's an alternative DSA deployment option using Apptainer (used by University of Florida) found [here](https://github.com/DigitalSlideArchive/digital_slide_archive/tree/slurm/devops/singularity-minimal), however, Podman is recommended for its stability and ease of configuration.

### Job Execution

Now for the second use case of Docker, executing `slicer_cli_web` jobs, we use Apptainer (formerly known as singularity) and optionally slurm. Most of our research partners choose to use DSA Slurm execution. We have working DSA slurm deployments with (Pitt, Tulane, and UF). To enable Apptainer/slurm jobs you have to install several python plugins to the Girder/worker environments (see requirements and the DSA Slurm Reference for more information).


## Requirements

For Podman deployment:
- [Podman](https://podman.io/docs) installed on host system
- (TODO: add `devops/podman` example)


For Apptainer job execution:
- [Apptainer](https://apptainer.org/docs/admin/main/installation.html)
- [Girder Worker Singularity](https://github.com/girder/girder_worker/tree/slurm/girder_worker/singularity) plugin
- [Slicer CLI Web Singularity](https://github.com/girder/slicer_cli_web/tree/slicer-cli-web-singularity/slicer_cli_web/singularity) plugin


For Apptainer job execution using Slurm:
- All above Apptainer requirements
- [Girder Worker Slurm](https://github.com/girder/girder_worker/tree/slurm/girder_worker/slurm) plugin
- Apptainer installed on all slurm nodes (login & compute)
- Shared filesystem visible to worker and compute nodes
- Slurm login node access (`squeue`, `sinfo`, `scontrol`, etc.) for `girder_worker`
- See [DSA Slurm (Reference Docs)](https://github.com/DigitalSlideArchive/digital_slide_archive/tree/slurm/devops/slurm) for more details


## Credentials

TODO: unsure of what to put here, ask David
