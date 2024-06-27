============================================================
Digital Slide Archive via Docker Compose with Remote Workers
============================================================

This directory has a docker compose set up that can run the Digital Slide Archive on one machine and start an arbitrary number of remote workers on other machines.

See the main comments about docker compose in the devops/dsa/README.rst file.

Options
-------

There are several options that can be specified by environment variables:

- ``DSA_WORKER_API_URL``: The URL that the workers use to reach the server's api interface.  This is typically something like ``http://<server host>:<server port>/api/v1``.  It has to be specified when starting the server.

- ``DSA_RABBITMQ_HOST``: The host name (and possibly port) that the workers use to contact the RabbitMQ messaging queue.  This is typically something like ``<server host>``.  It has to be specified when starting a worker.

- ``DSA_USER``: This is the user and group that the server or worker is run as; it is used to start other docker containers as needed, so should be part of the docker group.  This is usually ``$(id -u):$(id -g)``.  This is specified for both the server and the workers.

- ``RABBITMQ_USER``: The name of the user for RabbitMQ that the worker will connect to.  This defaults to ``girder``.  This is specified for both the server and the workers.

- ``RABBITMQ_PASSWORD``: The password of the user for RabbitMQ that the worker will connect to.  This defaults to ``girder1234``.  This is specified for both the server and the workers.  Note for security, RabbitMQ on the server could be set to only accept connections from the local system and specific IP addresses of the workers.

- ``DSA_WORKER_CONCURRENCY``: The number of jobs a worker can run at one time.  This can be different for each worker.  It defaults to ``2``.

Example
-------

Suppose we have a server at ``dsa-server.kitware.com`` on port 8080 and workers at ``dsa-worker1.kitware.com`` and ``dsa-worker2.kitware.com``, then we could start the server with the command::

    DSA_WORKER_API_URL=https://dsa-server.kitware.com:8080/api/v1 DSA_USER=$(id -u):$(id -g) docker compose --profile server up -d

Each worker gets started the same way::

    DSA_RABBITMQ_HOST=dsa-server.kitware.com DSA_USER=$(id -u):$(id -g) docker compose --profile worker up -d

Note how ``--profile`` is used to determine whether the server or a worker is started.
