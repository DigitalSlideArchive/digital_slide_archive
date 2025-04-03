Migration Guide
===============

This document is intended to help transition between major versions of the Digital Slide Archive.  The current installation method uses ``docker compose`` and is based on Girder 3.x.

From deploy_docker.py to docker compose
---------------------------------------

Prior to 2021, the Digital Slide Archive used the ``deploy_docker.py`` script.  If you have deployed the software via another means, these instructions will need some adjustments.

The ``deploy_docker.py`` script was developed prior to docker compose handling all of the desired features.  If you are using command line options on ``deploy_docker.py``, you will need to figure out how each of those translates to the docker compose notation.  For the default deployment without any command line options, you can switch by doing::

    chown -R $(id -u):$(id -g) ~/.dsa

The, add ``docker-compose.override.yml`` to the ``devops/dsa`` directory, replacing ``/home/ubuntu`` with the resolution of ``~``::

    ---
    services:
      girder:
        volumes:
          - /home/ubuntu/.dsa/assetstore:/opt/digital_slide_archive/assetstore
          - /home/ubuntu/.dsa/logs:/logs
      mongodb:
        volumes:
          - /home/ubuntu/.dsa/db:/data/db

Now, from the ``devops/dsa`` directory, ``docker compose`` will work.


From Girder 2.x and the HistomicsTK Repository
----------------------------------------------

The Digital Slide Archive deployment was originally included as part of the HistomicsTK repository and used Girder 2.x as the underlying server.  To migrate from a Girder 2.x instance to the version in this repository, no special changes are needed -- just use the current ``deploy_docker.py`` script from this repository.

Mongo
-----

By default, the latest major version of MongoDB is used.  However, Mongo does not automatically upgrade the database files to work with more than one major version beyond the last update.  For instance, a database created in Mongo 3.4 will work with Mongo 3.6 but not Mongo 4.0.

If you have a running instance of the Digital Slide Archive, you can find out what version of Mongo the database is compatible to by issuing the command::

  docker exec histomicstk_mongodb mongo girder --eval \
  'db.adminCommand({getParameter: 1, featureCompatibilityVersion: 1})'

If this isn't the current version of Mongo, you can upgrade the database's compatibility version.  For instance, the command::

  docker exec histomicstk_mongodb mongo girder --eval \
  'db.adminCommand({setFeatureCompatibilityVersion: "4.2"})'

would upgrade to Mongo 4.2.

You can start the Digital Slide Archive with an older version of Mongo by specifying the version in your ``docker-compose.override.yml`` file as part of the mongo container's image name.  If your database is old enough, you might need to move one major version at a time, adjusting the compatibility version each time.
