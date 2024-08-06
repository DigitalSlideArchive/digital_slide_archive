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

License
-----------------------------------------------------------

The Digital Slide Archive is made available under the Apache License, Version 2.0. For more details, see `LICENSE <https://github.com/DigitalSlideArchive/digital_slide_archive/blob/master/LICENSE>`_

Community
-----------------------------------------------------------

`Discussions <https://github.com/DigitalSlideArchive/digital_slide_archive/discussions>`_ | `Issues <https://github.com/DigitalSlideArchive/digital_slide_archive/issues>`_ | `Contact Us <https://www.kitware.com/contact-us/>`_

Installation
------------

For installation instructions, see the complete `docker compose example <./devops/dsa>`_.

For local development including HistomicsUI, there are some `devops <./devops>`_ scripts.

There is a `migration guide <./docs/migration.rst>`_  from the Girder 2 version or from the ``deploy_docker.py`` script.

Adding Docker Tasks
-------------------

Docker tasks conforming to the `slicer_cli_web <https://github.com/girder/slicer_cli_web>`_ module's requirements can be added.  These tasks appear in the HistomicsUI interface and in the Girder interface.  An administrator can add a Docker image by going to the slicer_cli_web plugin settings and entering the Docker image name there.  For instance, to get the HistomicsTK tasks, add ``dsarchive/histomicstk:latest``.

To use a docker image from a docker repository that requires authentication, see the comments on how to pass through authenticaition in the ``docker-compose.yml`` file.  On the host machine (and the worker machines if they are separate), login to the docker repository, saving credentials.  This could be done with the command ``docker login <repository>`` which will then prompt for username and password.  Other docker config values can be set this way, too.

Funding
-------
This work was funded in part by the `NIH grant U24-CA194362-01 <http://grantome.com/grant/NIH/U24-CA194362-01>`_.
