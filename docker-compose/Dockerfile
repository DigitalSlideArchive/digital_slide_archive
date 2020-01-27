FROM nikolaik/python-nodejs:python3.7-nodejs12
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

# This prevents gdal from complaining that it can't write aux.xml files.
ENV GDAL_PAM_PROXY_DIR=/tmp/gdal

# See logs faster; don't write pyc or pyo files
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Install libfuse.  This allows better access to files on S3
RUN apt-get update && \
    apt-get install -y fuse && \
    rm -rf /var/lib/apt/lists/*

# add a directory for girder mount
RUN mkdir -p /fuse --mode=a+rwx

# By using --no-cache-dir the Docker image is smaller
RUN pip install --pre --no-cache-dir \
    # histomicui installs all of our absolutely required packages \
    histomicsui \
    # large_image[all] adds all tile sources and memcached support \
    large_image[all] \
    # large_image_tasks[girder,worker] installs a task for converting some \
    # otherwise unreadable images \
    large_image_tasks[girder,worker] \
    # girder[mount] adds dependencies to show tiles from S3 assets \
    girder[mount] \
    # You could add additional girder plugins here (e.g.,
    # girder-virtual-folders or girder-dicom-viewer)
    # Use prebuilt wheels whenever possible \
    --find-links https://girder.github.io/large_image_wheels

# Improve how celery restarts failed jobs
RUN echo 'task_reject_on_worker_lost = True' >> /usr/local/lib/python3.7/site-packages/girder_worker/celeryconfig.py && \
    echo 'task_acks_late = True' >> /usr/local/lib/python3.7/site-packages/girder_worker/celeryconfig.py

# Copy a config file for girder worker
COPY worker.local.cfg /usr/local/lib/python3.7/site-packages/girder_worker/worker.local.cfg

# Build the girder web client
RUN girder build && \
    # Git rid of unnecessary files to keep the docker image smaller
    find /usr/local/lib/python3.7 -name node_modules -exec rm -rf {} \+ && \
    rm -rf /tmp/npm*
