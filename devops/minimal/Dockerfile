FROM python:3.13-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    git \
    && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Use nvm to install node
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash

RUN . ~/.bashrc && \
    nvm install 20 && \
    nvm alias default 20 && \
    nvm use default && \
    ln -s $(dirname `which npm`) /usr/local/node

ENV PATH="/usr/local/node:$PATH"

RUN npm --version && node --version

RUN curl -LJ https://github.com/krallin/tini/releases/download/v0.19.0/tini -o /usr/bin/tini && \
    chmod +x /usr/bin/tini

RUN pip install \
    girder-homepage \
    # girder-client is used to get sample data.  If you don't fetch sample \
    # data, it isn't necessary \
    girder-client \
    --no-cache-dir

# build locally until some versions for girder-5 are less confusing
RUN cd /opt && \
    git clone https://github.com/girder/large_image && \
    cd /opt/large_image && \
    git checkout girder-5 || true && \
    pip install --no-cache-dir --find-links https://girder.github.io/large_image_wheels -e .[memcached] -rrequirements-dev.txt && \
    cd /opt/large_image/girder/girder_large_image/web_client && \
    npm ci || npm install && \
    npm run build && \
    cd /opt/large_image/girder_annotation/girder_large_image_annotation/web_client && \
    npm ci || npm install && \
    npm run build && \
    cd /opt/large_image/sources/dicom/large_image_source_dicom/web_client && \
    npm ci || npm install && \
    npm run build

# build locally until some versions for girder-5 are less confusing
RUN cd /opt && \
    git clone https://github.com/DigitalSlideArchive/HistomicsUI && \
    cd /opt/HistomicsUI && \
    git checkout girder-5 || true && \
    # Unpin since we are using local installs \
    sed -i 's/==1\.3.*'\''/'\''/g' setup.py && \
    pip install --no-cache-dir -e .[analysis] && \
    cd /opt/HistomicsUI/histomicsui/web_client && \
    npm ci || npm install && \
    # This builds both the app and the plugin \
    npm run build

COPY provision.py .

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD python provision.py --sample-data --slicer-cli-image= && (celery -A girder_worker.app worker -Q local --concurrency 4 &) && girder serve --database mongodb://mongodb:27017/girder --host=0.0.0.0
