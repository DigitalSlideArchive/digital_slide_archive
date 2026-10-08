FROM dsarchive/dsa_common:latest
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

RUN apt update \
    && apt install -y software-properties-common \
    && add-apt-repository -y ppa:apptainer/ppa \
    && apt update \
    && apt install -y apptainer-suid
