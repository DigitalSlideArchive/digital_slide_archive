FROM dsarchive/dsa_common:latest
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

RUN add-apt-repository -y ppa:apptainer/ppa \
    && apt update \
    && apt install -y apptainer-suid
