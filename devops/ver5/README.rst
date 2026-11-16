===================================================
Digital Slide Archive via Docker Compose (Girder 5)
===================================================

This directory contains a complete docker compose set up for the Digital Slide Archive based on Girder 5.  It uses the ``dsarchive/dsa_common_5`` docker image, which is built from ``dsa5.Dockerfile`` at the root of this repository.

The Girder 3 based deployment, which uses the ``dsarchive/dsa_common`` docker image, is in `devops/dsa <../dsa>`_.  The general instructions in the `devops/dsa README <../dsa/README.rst>`_ (prerequisites, hardware requirements, permissions, private docker registries, and database backup) also apply here.  This document covers what is different and how to upgrade an existing deployment.

Start
-----

Change to this directory::

    cd digital_slide_archive/devops/ver5/

To get the most recent built docker images, do::

    docker compose pull

To start the Digital Slide Archive::

    DSA_USER=$(id -u):$(id -g) docker compose up

The girder instance can now be accessed at http://localhost:8080.  For a new database, this creates an ``admin`` user with a password of ``password``.

To stop the Digital Slide Archive::

    docker compose down -v

Upgrading from devops/dsa (dsa_common) to devops/ver5 (dsa_common_5)
--------------------------------------------------------------------

The Girder 5 deployment uses the same Mongo database (named ``girder``) and the same assetstore files as the Girder 3 deployment.  Upgrading consists of stopping the old deployment, making the existing database and assetstore directories available to the new one, and carrying over any customizations you have made.

The two deployments have not been tested running both at the same time against the same database files. It is recommended you stop the older version before starting the newer version. By default they also both use port 8080.

The changes in Girder itself are described in the 3.x to 5.x section of the `Girder migration guide <https://girder.readthedocs.io/en/latest/migration-guide.html>`_ (the source is ``docs/migration-guide.rst`` in the `Girder repository <https://github.com/girder/girder>`_).  That guide is written for plugin developers; this document covers the Digital Slide Archive docker compose deployment.  If you maintain your own Girder plugins or client code, read the Girder guide as well.

1. Back up (recommended)
~~~~~~~~~~~~~~~~~~~~~~~~

With the existing deployment running, back up the database from the ``devops/dsa`` directory::

    docker compose exec mongodb /usr/bin/mongodump --db girder --archive --gzip > dsa_girder.dump.gz

Keep this backup until you are satisfied with the upgrade.  If you later want to return to the Girder 3 deployment and it has problems with the database, restore this backup (see the Database Backup section of the `devops/dsa README <../dsa/README.rst>`_).

Files in the assetstore are not modified by the upgrade; the database is intended to be compatible between major versions, but downgrading has not been extensively tested.

2. Stop the existing deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

From the ``devops/dsa`` directory::

    docker compose down -v

If you use additional compose files, pass the same ``-f`` options that you use when starting the deployment.

3. Make the existing data available
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, both deployments store data in directories next to their ``docker-compose.yml`` file: ``db`` for the database and ``assetstore`` for the default assetstore.  Do one of the following.

**Either** move the directories::

    mv ../dsa/db/* db/
    mv ../dsa/assetstore/* assetstore/

**or** leave them where they are and refer to them from a ``docker-compose.override.yml`` file in the ``devops/ver5`` directory::

    ---
    services:
      girder:
        volumes:
          - ../dsa/assetstore:/assetstore
      mongodb:
        volumes:
          - ../dsa/db:/data/db

If your existing deployment already mounts the database or assetstores from other locations, use the same host paths and the same paths inside the container in the new override file.  Assetstores record their path inside the container in the database, so the paths inside the container must not change.

The ``logs`` directory does not need to be moved.

4. Carry over your customizations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you use any overrides or local provisioning files, copy your ``docker-compose.override.yml`` (or other additional compose file) and any custom provisioning yaml file to the ``devops/ver5`` directory, and then adjust them for the differences listed below.  Extra volume mounts, ``DSA_PORT``, ``DSA_WORKER_CONCURRENCY``, ``DOCKER_CONFIG``, and ``GIRDER_SETTING_*`` environment variables work as before.

**girder.cfg is no longer used.**  Remove any mount of a file to ``/etc/girder.cfg``.  The values that were in that file are now set with environment variables on the ``girder`` service.  See the `Girder configuration documentation <https://girder.readthedocs.io/en/latest/configuration.html>`_ for the full list of environment variables.  Any Girder setting can also be set with a ``GIRDER_SETTING_*`` variable, and these take precedence over values stored in the database.

.. list-table::
   :header-rows: 1

   * - ``girder.cfg`` entry
     - Girder 5 equivalent
   * - ``[database] uri``
     - ``GIRDER_MONGO_URI``
   * - ``[server] mode``
     - ``GIRDER_SERVER_MODE``.  This now defaults to ``production``; the Girder 3 file used ``development``.
   * - ``[cache] enabled``
     - ``GIRDER_SETTING_CORE_CACHE_ENABLED``
   * - ``[large_image] cache_backend``, ``cache_memcached_url``
     - ``LARGE_IMAGE_CACHE_BACKEND`` (now ``redis``), ``LARGE_IMAGE_CACHE_REDIS_URL``, ``LARGE_IMAGE_CACHE_REDIS_PASSWORD``
   * - ``[large_image] cache_tilesource_maximum``
     - ``LARGE_IMAGE_CACHE_TILESOURCE_MAXIMUM``
   * - ``[histomicsui] restrict_downloads``
     - ``HISTOMICSUI_RESTRICT_DOWNLOADS``
   * - ``[logging]``
     - Not used.  See the note on logging, below.
   * - ``[global] server.socket_host``
     - The ``--host`` option of ``girder serve`` in ``start_girder.sh``.

**Memcached is replaced by Redis.**  There is no default ``memcached`` service. The ``redis`` service is used both for tile caching and for Girder's notifications.  Its memory use is the smaller of a proportion of system memory (``REDIS_MAX_MEMORY_PROPORTION``, default ``0.125``) and a fixed size (``REDIS_MAX_MEMORY_BYTES``, default ``4096MB``); set these in the environment of the ``redis`` service to change them.

**The worker broker is set by environment variables.**  The ``worker.broker`` and ``worker.backend`` settings in the provisioning yaml file and the ``worker.local.cfg`` file are no longer used.  Instead, ``CELERY_BROKER_URL`` and ``CELERY_RESULT_BACKEND`` are set on both the ``girder`` and ``worker`` services.  If you use a non-default RabbitMQ user, password, or host, change these values in both services.  These are Celery's own variables.  The Girder documentation describes ``GIRDER_WORKER_BROKER`` and ``GIRDER_WORKER_BACKEND`` for the same purpose; if both are set, Celery uses the ``CELERY_*`` values.  For workers on other machines, see `devops/external-worker-5 <../external-worker-5>`_.

**There is no rebuild-client step.**  Remove ``rebuild-client`` from your provisioning yaml file.  In Girder 5, each plugin builds its own web client, and there is no ``girder build`` command.  Plugins that are part of the docker image are already built.  If you install a plugin from source via the ``pip`` list and it has client-side code that is not prebuilt, add a ``shell`` entry to build it, for instance::

    shell:
      - bash -c "cd <path to the plugin>/web_client && npm ci && npm run build"

**Plugins must be compatible with Girder 5.**  Check each entry in the ``pip`` list of your provisioning file (including the ``worker`` section).  Remove version limits that were there to stay on Girder 3 (such as ``girder-oauth<5``), and use the Girder 5 branch or release of plugins that are installed from git (for many plugins in the DigitalSlideArchive organization this is a branch named ``girder-5``).  The image already contains the ``oauth``, ``ldap``, ``user_quota``, ``homepage``, ``hashsum_download``, ``virtual_folders``, ``import_tracker``, ``slicer_cli_web``, ``large_image``, ``histomicsui``, and ``girder_assetstore`` plugins; these do not need to be listed.  A plugin that has not been updated for Girder 5 will not work.  To update a plugin of your own, follow the `Girder migration guide <https://girder.readthedocs.io/en/latest/migration-guide.html>`_.

**Source mounts for development.**  If you mount local source directories over those in the image, the source must be on a Girder 5 compatible branch, and its web client needs to be built with ``npm`` in its ``web_client`` directory.

5. Start the new deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~

From the ``devops/ver5`` directory::

    docker compose pull
    DSA_USER=$(id -u):$(id -g) docker compose up -d

Use the same ``DSA_USER`` value as before so that the existing database and assetstore files remain accessible.


6. Other changes
~~~~~~~~~~~~~~~~

- **Logging.**  Girder no longer writes its own log files.  All services log to the docker log (``docker compose logs``).  The additional ``logging`` service copies these to rotated files in the ``logs`` directory, one per service; the ``girder`` service is written to ``info.log``.  The ``logging`` service and the ``logs`` mount are optional.

- **HTTP only cookies.**  ``core.http_only_cookies`` is now turned on by default.  If you have custom client code that reads the Girder token from the cookie, either change it or set ``GIRDER_SETTING_CORE_HTTP_ONLY_COOKIES`` to ``false``.

- **Local worker.**  The ``girder`` container also runs a celery worker for the ``local`` queue.  Work that Girder 3 ran in a background thread of the server process, such as importing data from an assetstore, is run there.  The separate ``worker`` service is still used for Slicer CLI tasks.

- **Provisioning order.**  Slicer CLI docker images listed in the provisioning file are now pulled and loaded after the server has started rather than before, so the server is reachable while they are being pulled.

- **Reverse proxies.**  Notifications (such as job progress) are now sent to the browser over a websocket rather than by polling, so a reverse proxy in front of Girder must pass websocket connections through.  See the example nginx configuration in the `Girder deployment documentation <https://girder.readthedocs.io/en/latest/deployment.html>`_.  If Girder is served from somewhere other than the root of the url, also set ``GIRDER_URL_ROOT`` on the ``girder`` service.

- **Container names.**  The compose project name comes from the directory name, so containers are named ``ver5-girder-1`` and so on rather than ``dsa-girder-1``.  Adjust any scripts that use the container names directly.
