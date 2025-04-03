FROM girder/tox-and-node
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

ENV LANG=en_US.UTF-8

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
    && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    find / -xdev -name '*.py[oc]' -type f -exec rm {} \+ && \
    find / -xdev -name __pycache__ -type d -exec rm -rf {} \+

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
    find / -xdev -name __pycache__ -type d -exec rm -rf {} \+

RUN curl -LJ https://github.com/krallin/tini/releases/download/v0.19.0/tini -o /usr/bin/tini && \
    chmod +x /usr/bin/tini

# Make a virtualenv with our preferred python
RUN virtualenv --python 3.11 /opt/venv && \
    find / -xdev -name __pycache__ -type d -exec rm -rf {} \+

ENV PATH="/opt/venv/bin:$PATH"

# Make sure core packages are up to date
RUN python --version && \
    pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -U tox wheel && \
    find / -xdev -name __pycache__ -type d -exec rm -rf {} \+

RUN . ~/.bashrc && \
    nvm install 22 && \
    nvm alias default 22 && \
    nvm use default && \
    rdfind -minsize 32768 -makehardlinks true -makeresultsfile false /root/.nvm && \
    nvm uninstall 14 && \
    rm /usr/local/node && \
    ln -s $(dirname `which npm`) /usr/local/node && \
    npm config set fetch-timeout 600000 && \
    rm -rf /root/.cache /root/.npm /tmp/* && \
    true

ENV SKIP_SOURCE_MAPS=true

# Clone packages and pip install what we want to be local
RUN cd /opt && \
    # Install gunicorn so we can use it instead of girder serve \
    pip install --no-cache-dir gunicorn && \
    git clone -b v4-integration https://github.com/girder/girder && \
    cd /opt/girder && \
    pip install --no-cache-dir -e .[mount] && \
    pip install --no-cache-dir -e clients/python && \
    cd girder/web && \
    npm ci && \
    npm run build && \
    find /opt -xdev -name node_modules -exec rm -rf {} \+ && \
    rm -rf /root/.cache /root/.npm /tmp/* && \
    find / -xdev -name __pycache__ -type d -exec rm -rf {} \+ && \
    true

RUN cd /opt/girder/worker && \
    pip install --no-cache-dir -e . && \
    \
    cd /opt/girder/plugins/worker && \
    pip install --no-cache-dir -e .[girder,worker] && \
    cd girder_plugin_worker/web_client && \
    npm ci && \
    npm run build && \
    find /opt -xdev -name node_modules -exec rm -rf {} \+ && \
    rm -rf /root/.cache /root/.npm /tmp/* && \
    find / -xdev -name __pycache__ -type d -exec rm -rf {} \+ && \
    true

# Girder plugins
RUN true && \
    cd /opt/girder/plugins/hashsum_download && \
    pip install --no-cache-dir -e . && \
    cd girder_hashsum_download/web_client && \
    npm ci && \
    npm run build && \
    cd /opt/girder/plugins/homepage && \
    pip install --no-cache-dir -e . && \
    cd girder_homepage/web_client && \
    npm ci && \
    npm run build && \
    cd /opt/girder/plugins/jobs && \
    pip install --no-cache-dir -e . && \
    cd girder_jobs/web_client && \
    npm ci && \
    npm run build && \
    cd /opt/girder/plugins/ldap && \
    pip install --no-cache-dir -e . && \
    cd girder_ldap/web_client && \
    npm ci && \
    npm run build && \
    cd /opt/girder/plugins/oauth && \
    pip install --no-cache-dir -e . && \
    cd girder_oauth/web_client && \
    npm ci && \
    npm run build && \
    cd /opt/girder/plugins/user_quota && \
    pip install --no-cache-dir -e . && \
    cd girder_user_quota/web_client && \
    npm ci && \
    npm run build && \
    cd /opt/girder/plugins/import_tracker && \
    pip install --no-cache-dir -e . && \
    cd girder_import_tracker/web_client && \
    npm ci && \
    npm run build && \
    # virtual_folders has no web_client \
    cd /opt/girder/plugins/virtual_folders && \
    pip install --no-cache-dir -e . && \
    cd /opt/girder/plugins/slicer_cli_web && \
    pip install --no-cache-dir -e . && \
    cd girder_slicer_cli_web/web_client && \
    npm ci && \
    npm run build && \
    find /opt -xdev -name node_modules -exec rm -rf {} \+ && \
    rm -rf /root/.cache /root/.npm /tmp/* && \
    find / -xdev -name __pycache__ -type d -exec rm -rf {} \+ && \
    true

RUN cd /opt && \
    git clone -b girder-5 https://github.com/girder/large_image && \
    cd /opt/large_image && \
    pip install --no-cache-dir --find-links https://girder.github.io/large_image_wheels -e .[memcached] -rrequirements-dev.txt && \
    cd /opt/large_image/girder/girder_large_image/web_client && \
    npm ci && \
    npm run build && \
    cd /opt/large_image/girder_annotation/girder_large_image_annotation/web_client && \
    npm ci && \
    npm run build && \
    cd /opt/large_image/sources/dicom/large_image_source_dicom/web_client && \
    npm ci && \
    npm run build && \
    rdfind -minsize 32768 -makehardlinks true -makeresultsfile false /opt/venv && \
    find /opt -xdev -name node_modules -exec rm -rf {} \+ && \
    rm -rf /root/.cache /root/.npm /tmp/* && \
    find / -xdev -name __pycache__ -type d -exec rm -rf {} \+ && \
    find . -name *js.map* -exec rm -r {} \+ && \
    true

RUN cd /opt && \
    git clone -b girder-5 https://github.com/DigitalSlideArchive/HistomicsUI && \
    cd /opt/HistomicsUI && \
    # Unpin since we are using local installs \
    sed -i 's/==1\.3.*'\''/'\''/g' setup.py && \
    pip install --no-cache-dir -e .[analysis] && \
    cd /opt/HistomicsUI/histomicsui/web_client && \
    npm ci && \
    # This builds both the app and the plugin \
    npm run build && \
    rdfind -minsize 32768 -makehardlinks true -makeresultsfile false /opt/venv && \
    find /opt -xdev -name node_modules -exec rm -rf {} \+ && \
    rm -rf /root/.cache /root/.npm /tmp/* && \
    find / -xdev -name __pycache__ -type d -exec rm -rf {} \+ && \
    find . -name *js.map* -exec rm -r {} \+ && \
    true

RUN cd /opt && \
    git clone -b girder-5 https://github.com/DigitalSlideArchive/girder_assetstore && \
    cd /opt/girder_assetstore && \
    pip install --no-cache-dir -e . && \
    cd /opt/girder_assetstore/girder_assetstore/web_client && \
    npm ci && \
    npm run build && \
    find /opt -xdev -name node_modules -exec rm -rf {} \+ && \
    rm -rf /root/.cache /root/.npm /tmp/* && \
    find / -xdev -name __pycache__ -type d -exec rm -rf {} \+ && \
    find . -name *js.map* -exec rm -r {} \+ && \
    true

# When running the worker, adjust some settings
RUN echo 'task_reject_on_worker_lost = True' >> /opt/girder/worker/girder_worker/celeryconfig.py && \
    echo 'task_acks_late = True' >> /opt/girder/worker/girder_worker/celeryconfig.py

COPY . /opt/digital_slide_archive

ENV PATH="/opt/digital_slide_archive/devops/dsa/utils:$PATH"

WORKDIR /opt/HistomicsUI

# add a variety of directories
RUN mkdir -p /fuse --mode=a+rwx && \
    mkdir /logs && \
    mkdir /assetstore && \
    mkdir /mounts --mode=a+rwx

RUN cp /opt/digital_slide_archive/devops/dsa/utils/.vimrc ~/.vimrc

ARG DSA_VERSIONS
ENV DSA_VERSIONS="$DSA_VERSIONS"

# Better shutdown signalling
ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["bash"]
