=====================
Digital Slide Archive
=====================

Organize, visualize, and analyze histology images.

The `Digital Slide Archive`_ organizes and managed whole slide image (WSI) files using Girder_.  It has a dedicated interface to select WSI, add annotations manually, and to run analysis and algorithms on all or parts of images.

Girder provides authentication, access control, and diverse storage options, including using local file systems and Amazon S2.  WSI images are read and displayed via the large_image_ module.  Algorithms are containerized using Docker_ and are run using the slicer_cli_web_ Girder plugin.  These can be run on multiple worker machines via `Girder Worker`_ and celery_.

A set of common algorithms are provided by HistomicsTK_.

Installation
------------

Linux
=====

In linux with Python 2.7, Python 3.5, 3.6, or 3.7:

Prerequisites:

- MongoDB must be installed and running.
- An appropriate version of Python must be installed.

```
pip install digital-slide-archive --find-links https://girder.github.io/large_image_wheels
girder build
girder serve
```

To use Girder Worker:

```
pip install girder_slicer_cli_web[worker]
GW_DIRECT_PATHS=true girder_worker -l info -Ofair --prefetch-multiplier=1
```

The first time you start the Digital Slide Archive, you'll also need to configure Girder with at least one user and one assetstore (see the Girder_ documentation).  Additionally, it is recommended that you install the HistomicsTK_ algorithms.  This can be done going to the Admin Console, Plugins, Slicer CLI Web settings.  Set a default task upload folder, then import the `dsarchive/histomicstk:latest` docker image.

Docker
======

TODO: copy from HistomicsTK documentation.

Funding
-------
This work is funded in part by the NIH grant U24-CA194362-01_.

.. _Digital Slide Archive: https://github.com/DigitalSlideArchive
.. _Docker: https://www.docker.com/
.. _Kitware: https://www.kitware.com/
.. _U24-CA194362-01: http://grantome.com/grant/NIH/U24-CA194362-01

.. _Girder: http://girder.readthedocs.io/en/latest/
.. _Girder Worker: https://girder-worker.readthedocs.io/en/latest/
.. _large_image: https://github.com/girder/large_image
.. _slicer_cli_web: https://github.com/girder/slicer_cli_web
.. _slicer execution model: https://www.slicer.org/slicerWiki/index.php/Slicer3:Execution_Model_Documentation
.. _Discourse forum: https://discourse.girder.org/c/histomicstk
.. _Gitter Chatroom: https://gitter.im/DigitalSlideArchive/HistomicsTK?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge
.. _celery: http://www.celeryproject.org/
.. _HistomicsTK: https://github.com/DigitalSlideArchive/HistomicsTK
