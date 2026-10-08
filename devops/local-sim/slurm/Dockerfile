FROM ubuntu:26.04

# Slurm node (slurmctld + slurmd combined, simulating a single-node cluster)
# plus apptainer, since slurm jobs run apptainer SIFs on the "compute node".
RUN apt update \
    && DEBIAN_FRONTEND=noninteractive apt install -y \
        software-properties-common munge slurm-wlm slurm-client \
    && add-apt-repository -y ppa:apptainer/ppa \
    && apt update \
    && DEBIAN_FRONTEND=noninteractive apt install -y apptainer-suid \
    && rm -rf /var/lib/apt/lists/*

COPY slurmnode.sh /opt/slurmnode.sh

ENTRYPOINT ["bash", "/opt/slurmnode.sh"]
