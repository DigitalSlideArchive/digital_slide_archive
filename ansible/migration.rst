Migration Guide
===============

This document is intended to help transition between major versions of the Digital Slide Archive.  The reference deployment of the Digital Slide Archive uses the ``deploy_docker.py`` script.  If you have deployed the software via another means, these instructions will need some adjustments.

From Girder 2.x and the HistomicsTK Respository
-----------------------------------------------

The Digital Slide Archive deployment was originally included as part of the HistomicsTK repository and used Girder 2.x as the underlying server.  To migrate from a Girder 2.x instance to the version in this repository, no special changes are needed -- just use the current ``deploy_docker.py`` script from this repository.

Going Back
++++++++++

If, for some reason, you need to move back to Girder 2, you will need to adjust some values in the Mongo database.  This is because, as part of the update, the version of ``large_image`` is updated, and it has a name change for one of the tile sources.  Before or after downgrading via the old script, you'll need to use a mongo client to connect to the mongo database (for instance, by running ``docker exec -it histomicstk_mongodb mongo girder``).  Then, issue the Mongo command ``db.item.updateMany({"largeImage.sourceName": "openslide"}, {$set: {"largeImage.sourceName": "svs"}})``.

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

You can start the Digital Slide Archive with an older version of Mongo by specifying the version on the command line (e.g., ``deploy_docker.py --mongo=3.6``).  If your database is old enough, you might need to move one major version at a time, adjusting the compatibility version each time.
