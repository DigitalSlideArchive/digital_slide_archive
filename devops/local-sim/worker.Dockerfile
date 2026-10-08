FROM dsa_common_apptainer:g3

# The worker needs the slurm client tools and munge to submit and monitor
# jobs on the slurm "cluster" container.
RUN apt update \
    && DEBIAN_FRONTEND=noninteractive apt install -y slurm-client munge \
    && rm -rf /var/lib/apt/lists/*

COPY start_worker_slurm.sh /opt/start_worker.sh
