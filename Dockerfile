FROM girder/tox-and-node
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

ENV LANG en_US.UTF-8

# Install some additional packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # For ease of running tox tests inside containers \
    iptables \
    dnsutils \
    # Install some additional packages for convenience when testing \
    bsdmainutils \
    iputils-ping \
    telnet-ssl \
    tmux \
    # For developer convenience \
    nano \
    jq \
    # Needed for su command
    # sudo \
    && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    find / -xdev -name '*.py[oc]' -type f -exec rm {} \+ && \
    find / -xdev -name __pycache__ -type d -exec rm -r {} \+

# Install docker command line tools.  If docker is unavailable, this will do no
# harm.  If the host system isn't ubuntu, this should still allow debug.
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list >/dev/null && \
    ls -al /etc/apt/sources.list.d && \
    cat /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    docker-ce-cli \
    && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    find / -xdev -name '*.py[oc]' -type f -exec rm {} \+ && \
    find / -xdev -name __pycache__ -type d -exec rm -r {} \+

RUN curl -LJ https://github.com/krallin/tini/releases/download/v0.19.0/tini -o /usr/bin/tini && \
    chmod +x /usr/bin/tini

# Make a virtualenv with our preferred python
RUN virtualenv --python 3.9 /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Make sure core packages are up to date
RUN python --version && \
    pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -U tox wheel

# Clone packages and pip install what we want to be local
RUN cd /opt && \
    git clone https://github.com/girder/girder && \
    cd /opt/girder && \
    pip install --no-cache-dir -e .[mount] && \
    pip install --no-cache-dir -e clients/python

RUN cd /opt && \
    git clone https://github.com/girder/girder_worker_utils && \
    cd /opt/girder_worker_utils && \
    pip install --no-cache-dir -e .

RUN cd /opt && \
    git clone https://github.com/girder/girder_worker && \
    cd /opt/girder_worker && \
    pip install --no-cache-dir -e .[girder,worker]

RUN cd /opt && \
    git clone https://github.com/DigitalSlideArchive/import-tracker.git && \
    cd /opt/import-tracker && \
    pip install --no-cache-dir -e .

RUN cd /opt && \
    git clone https://github.com/girder/slicer_cli_web && \
    cd /opt/slicer_cli_web && \
    pip install --no-cache-dir -e .

RUN cd /opt && \
    git clone https://github.com/girder/large_image && \
    cd /opt/large_image && \
    pip install --no-cache-dir --find-links https://girder.github.io/large_image_wheels -e .[memcached] -rrequirements-dev.txt && \
    # Reduice docker size by de-duplicating some libraries that get installed \
    rdfind -minsize 1048576 -makehardlinks true -makeresultsfile false /opt/venv

RUN cd /opt && \
    git clone https://github.com/DigitalSlideArchive/HistomicsUI && \
    cd /opt/HistomicsUI && \
    pip install --no-cache-dir -e .[analysis]

# Install additional girder plugins
RUN pip install --no-cache-dir --pre \
    girder-archive-access \
    girder-dicom-viewer \
    girder-homepage \
    girder-ldap \
    girder-resource-path-tools \
    girder-user-quota \
    girder-virtual-folders \
    girder-xtk-demo

# Build the girder web client
RUN NPM_CONFIG_FUND=false NPM_CONFIG_AUDIT=false NPM_CONFIG_AUDIT_LEVEL=high NPM_CONFIG_LOGLEVEL=warn NPM_CONFIG_PROGRESS=false NPM_CONFIG_PREFER_OFFLINE=true \
    girder build --dev && \
    # Get rid of unnecessary files to keep the docker image smaller \
    find /opt -xdev -name node_modules -exec rm -rf {} \+ && \
    find /opt -name package-lock.json -exec rm -f {} \+ && \
    rm -rf /tmp/* ~/.npm

# Install phantomjs for testing
RUN npm install -g phantomjs-prebuilt --unsafe-perm && \
    rm -rf /tmp/* ~/.npm

# When running the worker, adjust some settings
RUN echo 'task_reject_on_worker_lost = True' >> /opt/girder_worker/girder_worker/celeryconfig.py
RUN echo 'task_acks_late = True' >> /opt/girder_worker/girder_worker/celeryconfig.py

COPY . /opt/digital_slide_archive

ENV PATH="/opt/digital_slide_archive/devops/dsa/utils:$PATH"

WORKDIR /opt/HistomicsUI

# add a variety of directories
RUN mkdir -p /fuse --mode=a+rwx && \
    mkdir /logs && \
    mkdir /assetstore && \
    mkdir /mounts --mode=a+rwx

RUN cp /opt/digital_slide_archive/devops/dsa/utils/.vimrc ~/.vimrc && \
    cp /opt/digital_slide_archive/devops/dsa/girder.cfg /etc/girder.cfg && \
    cp /opt/digital_slide_archive/devops/dsa/worker.local.cfg /opt/girder_worker/girder_worker/.

# Better shutdown signalling
ENTRYPOINT ["/usr/bin/tini", "--"]

CMD bash
