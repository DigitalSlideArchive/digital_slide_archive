Digital Slide Archive
=====================

The Digital Slide Archive is a system for working with large microscopy images.

- Organize images from a variety of assetstores, such as local file systems and S3.

- Provide user access controls.

- Image annotation and review.

- Run algorithms on all or parts of images.

Website
-------

See `<https://digitalslidearchive.github.io/digital_slide_archive/>`_ for information about the system.

Demo Instance
-------------

`http://demo.kitware.com/histomicstk/histomicstk <http://demo.kitware.com/histomicstk/histomicstk#?image=5c74528be62914004b10fd1e>`_.

Installation
------------

For installation instructions, see the complete `docker-compose example <./devops/dsa>`_.

There is an older method that doesn't use docker-compose.  See `here <./ansible>`_.

For local development including HistomicsUI, there are some `devops <./devops>`_ scripts.

There is a `migration guide <./ansible/migration.rst>`_  from the Girder 2 version and from the ``deploy_docker.py`` script.

Adding Docker Tasks
-------------------

Docker tasks conforming to the `slicer_cli_web <https://github.com/girder/slicer_cli_web>`_ module's requirements can be added.  These tasks appear in the HistomicsUI interface and in the Girder interface.  An administrator can add a Docker image by going to the slicer_cli_web plugin settings and entering the Docker image name there.  For instance, to get the HistomicsTK tasks, add ``dsarchive/histomicstk:latest``.

Funding
-------
This work was funded in part by the `NIH grant U24-CA194362-01 <http://grantome.com/grant/NIH/U24-CA194362-01>`_.
