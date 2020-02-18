========================================
Digital Slide Archive via Docker Compose
========================================

This directory contains a docker-compose set up for the Digital Slide Archive.  It is intended to be fully functional while still being close to the minimal configuration necessary.

This does not have optional Girder plugins.  It will require editing the docker-compose.yml file to add mount points for additional data or for exposing additional ports.

Prerequsities:
--------------

Before using this, you need both Docker and docker-compose.  See the `official installation instructions <https://docs.docker.com/compose/install>`_.

The docker-compose file assumes certain file paths.  This has been tested on Ubuntu 18.04.  It will probably work on other Linux variants.

Get the Digital Slide Archive repository::

    git clone https://github.com/DigitalSlideArchive/digital_slide_archive

Start
-----

To start the Digital Slide Archive::

    CURRENT_UID=$(id -u):$(id -g) docker-compose up

This uses your current user id so that database files, logs, assetstore files, and temporary files are owned by the current user.  If you omit setting ``CURRENT_UID``, files may be created owned by root.

Note that this example does not add any default tasks or sample files.  By default, it creates an ``admin`` user with a password of ``password``.  You can log in with the admin user and use the Slicer CLI Web plugin settings to add default tasks (e.g., ``dsarchive/histomicstk:latest``).

Technical Details
-----------------

The Digital Slider Archive is built in Girder and Girder Worker.  Here, these are coordinated using docker-compose.  There are five containers that are started:

- `Girder <https://girder.readthedocs.io/>`_.  Girder is an asset and user management system.  It handles permissions and serves data via http.

- `MongoDB <https://www.mongodb.com/>`_.  Girder stores settings and information about users and assets in a MongoDB database.

- `Girder Worker <https://girder-worker.readthedocs.io/>`_.  Girder Worker is a task runner based on `Celery <https://celery.readthedocs.io/>`_ that has specific features to get authenticated data from Girder.

- `RabbitMQ <https://www.rabbitmq.com/>`_.  Girder communicates to Girder Worker through a broker.  In this configuration it is RabbitMQ.  Girder Worker can be run on multiple computers communicating with a single broker to distribute processing.

- `Memcached <https://memcached.org/>`_.  Memcached is used to cache data for faster access.  This is used for large tiled images.

The Digital Slide Archive relies on several Girder plugins:

- `large_image <https://github.com/girder/large_image>`_.  This provides a standardized way to access a wide range of image formats.  Images can be handled as multi-resolution tiles.  large_image has numerous tile sources to handle different formats.

- `HistomicUI <https://github.com/DigitalSlideArchive/HistomicsUI>`_.  This provides a user interface to examine and annotate large images.

- `Slicer CLI Web <https://github.com/girder/slicer_cli_web>`_.  This can run processing tasks in Docker containers.  Tasks report their capabilities via the Slicer CLI standard, listing required and optional inputs and outputs.  These tasks can be selected and configured via Girder and HistomicsUI and then run in a distributed fashion via Girder Worker.

Slicer CLI Web runs tasks in Docker containers and is itself running in a Docker container (in Girder for determining options and Girder Worker to run the task).  In order to allow a process in a docker container to create another docker container, the paths the docker executable and communications sockets are mounted from the host to the docker container.  This requires that the docker container be run in privileged mode.
