===========================================
Digital Slide Archive devops docker scripts
===========================================

Description
===========

This folder contains a set of scripts that are convenient to develop
Digital Slide Archive and HistomicsUI inside its docker container.

The following environment variables can be defined to affect how these scripts
run:

* ``HISTOMICS_TESTDATA_FOLDER``: Folder where test data will be located on the
  host computer.  Data from this folder can be imported into a filesystem
  assetstore from the ``/data`` directory.  This defaults to 
  ``~/.histomics_data`` if that directory is present.

* ``HISTOMICS_SOURCE_FOLDER``: If the HistomicsUI repository is available 
  locally, it is mounted into the running docker container to make development
  easier.  This defaults to a directory located at ``../../HistomicsUI`` in 
  relation to this README file.

* ``SLICER_CLI_WEB_SOURCE_FOLDER``: If the slicer_cli_web repository is 
  available locally, it is mounted into the running docker container to make
  development easier.  This defaults to a directory located at 
  ``../../slicer_cli_web`` in relation to this README file.

Scripts
=======

* ``deploy.sh``: wrapper script around ``deploy_docker.py`` script to mount
  local host source and data folders. ``deploy_docker.py`` arguments can be added to the
  command line.
* ``build.sh``: Build the girder web client inside the docker container to build HistomicsUI plugin.
* ``test.sh``: Run HistomicsUI tests inside container.
* ``connect.sh``: convenience script to log in the docker container (wrapper
  around ``docker exec``).

Usage
=====

Before other commands, it is assumed you have checked out this repository, and, optionally, the HistomicsUI repository::

  $ git clone https://github.com:DigitalSlideArchive/digital_slide_archive
  $ git clone https://github.com:DigitalSlideArchive/HistomicsUI  

A typical use case of these scripts is when one develops Digital Slide Archive and HistomicsUI locally on their computer.  It is possible to run everything inside docker containers to simplify deployment. This is typically  done using ``deploy_docker.py`` in the ``ansible`` folder with the command::

  $ cd digital_slide_archive
  $ cd ansible
  $ python deploy_docker.py start

If you use this script, a copy of the source code is created inside the docker container.
This is not ideal to develop as one has to update this code to test their improvements. Instead, one
can now use ``deploy.sh`` in the ``devops`` folder. This will mount their local source
folder in their container::

  $ cd digital_slide_archive
  $ export HISTOMICS_TESTDATA_FOLDER=~/data/histomicsTK
  $ mkdir -p $HISTOMICS_TESTDATA_FOLDER
  $ devops/deploy.sh start --build

By default, the script expects the HistomicsUI repository to be checked out adjacent to the digital_slide_archive repository.

To simplify future calls, one can set the environment variables directly in their ``.bashrc`` file.

Make sure that HistomicsUI Girder plugin is up to date by recompiling it::

  $ devops/build.sh

If your are actively changing the client, you may want to watch the plugin::

  $ devops/build.sh --watch-plugin histomicsui

And finally run the tests::

  $ devops/test.sh

Migration
=========

If you were using these scripts with the Girder 2 / HistomicsTK deployment, they will work in nearly the same manner.  Before, you would have cloned the HistomicsTK repository.  Instead, you'll need to check out this (the digital_slide_archive) repository and the HistomicsUI repository.

All of the Girder plugin and user interface code was moved from the HistomicsTK repository to the HistomicsUI repository.  The exact direcories within the repository are slightly different: the UI (web client) moved from ``web_client`` to ``histomocsui/web_client``.  The server code moved from ``server`` to ``histomicsui`` code.  Tests now use the tox framework rather than cmake.
