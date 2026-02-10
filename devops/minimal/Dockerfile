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
    nvm install 14 && \
    nvm alias default 14 && \
    nvm use default && \
    ln -s $(dirname `which npm`) /usr/local/node

ENV PATH="/usr/local/node:$PATH"

RUN npm --version && node --version

RUN curl -LJ https://github.com/krallin/tini/releases/download/v0.19.0/tini -o /usr/bin/tini && \
    chmod +x /usr/bin/tini

RUN pip install \
    histomicsui \
    large_image[sources] \
    girder-homepage \
    # girder-client is used to get sample data.  If you don't fetch sample \
    # data, it isn't necessary \
    girder-client \
    --no-cache-dir \
    --find-links https://girder.github.io/large_image_wheels

RUN girder build

COPY girder.cfg /etc/.
COPY provision.py .

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD python provision.py --sample-data --slicer-cli-image= && girder serve --database mongodb://mongodb:27017/girder
