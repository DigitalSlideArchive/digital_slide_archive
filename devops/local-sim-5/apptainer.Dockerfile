FROM dsarchive/dsa_common_5:latest
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

RUN apt update \
    && apt install -y software-properties-common \
    && add-apt-repository -y ppa:apptainer/ppa \
    && apt update \
    && apt install -y apptainer-suid

# TODO: remove this overlay once the apptainer/slurm port is merged into the
# girder repository and dsa5.Dockerfile builds from a ref that contains it;
# the stock dsa_common_5 image will then already include everything below.
#
# Overlay the opt-in apptainer (singularity) and slurm job execution support
# from the girder `apptainer-port` branch onto the stock girder tree, and
# reinstall the two affected packages so that their entry points include the
# new worker plugins.  Only the python pieces are overlaid: the port makes no
# web client changes.
#
# The overlaid files are placed in ./girder-overlay by deploy.sh (extracted
# from a local girder checkout of the branch), so this image builds from the
# deployed copy of this directory without network access to the girder
# repository and always matches the checked-out branch, including local
# commits.
COPY girder-overlay/ /tmp/girder-overlay/

RUN cp -a /tmp/girder-overlay/worker/. /opt/girder/worker/ \
    && cp -a /tmp/girder-overlay/plugins/slicer_cli_web/. /opt/girder/plugins/slicer_cli_web/ \
    && pip install --no-cache-dir --force-reinstall --no-deps \
        -e /opt/girder/worker \
        -e /opt/girder/plugins/slicer_cli_web \
    && rm -rf /tmp/girder-overlay /root/.cache /tmp/* \
    && find /opt -xdev -name '__pycache__' -type d -exec rm -rf {} \+ \
    && true
