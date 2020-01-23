====================================
Digital Slide Archive docker scripts
====================================

Description
===========

This folder contains a set of scripts that are convenient to develop
Digital Slide Archive and HistomicsUI inside its docker container.

The following environment variable need to be defined for these scripts
to run:

* ``HISTOMICS_TESTDATA_FOLDER``: Folder in which the test data will be installed
  on the host computer. This allows one to not download the test data every time,
  but instead keep it directly on the host computer. If the container is removed,
  there is no need to download the data again.

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

A typical use case of these scripts is when one develops Digital Slide Archive and HistomicsUI locally on their computer.
It is possible to run everything inside docker containers to simplify deployment. This is typically
done using ``deploy_docker.py`` in the ``ansible`` folder with the command::

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
