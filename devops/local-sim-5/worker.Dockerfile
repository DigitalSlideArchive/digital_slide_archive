# The worker image is self-contained (rather than being built on top of the
# girder image) because docker compose builds services in parallel: the
# `dsa_common_apptainer:g5` tag that girder builds may not exist yet when the
# worker build runs.  The base, apptainer, and the apptainer/slurm port
# overlay steps are therefore identical to apptainer.Dockerfile (and share
# its build cache).
FROM dsarchive/dsa_common_5:latest

# TODO: remove this overlay once the apptainer/slurm port is merged into the
# girder repository and dsa5.Dockerfile builds from a ref that contains it;
# the stock dsa_common_5 image will then already include everything below.
# See apptainer.Dockerfile for details on the overlay and its provenance.
RUN apt update \
    && apt install -y software-properties-common \
    && add-apt-repository -y ppa:apptainer/ppa \
    && apt update \
    && apt install -y apptainer-suid

COPY girder-overlay/ /tmp/girder-overlay/

RUN cp -a /tmp/girder-overlay/worker/. /opt/girder/worker/ \
    && cp -a /tmp/girder-overlay/plugins/slicer_cli_web/. /opt/girder/plugins/slicer_cli_web/ \
    && pip install --no-cache-dir --force-reinstall --no-deps \
        -e /opt/girder/worker \
        -e /opt/girder/plugins/slicer_cli_web \
    && rm -rf /tmp/girder-overlay /root/.cache /tmp/* \
    && find /opt -xdev -name '__pycache__' -type d -exec rm -rf {} \+ \
    && true

# The worker needs the slurm client tools and munge to submit and monitor
# jobs on the slurm "cluster" container.  The slurm client version comes from
# the same ubuntu release as the slurm-wlm packages in ../slurm/Dockerfile,
# so the protocol versions match.
RUN apt update \
    && DEBIAN_FRONTEND=noninteractive apt install -y slurm-client munge \
    && rm -rf /var/lib/apt/lists/*

COPY start_worker_slurm.sh /opt/start_worker.sh
