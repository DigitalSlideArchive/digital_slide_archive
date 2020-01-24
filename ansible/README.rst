=============================
Install Digital Slide Archive
=============================

There are several ways to install the Digital Slide Archive and HistomicsUI.  If you intend to use the interface, use the Docker installation.  If you don't have docker installed, the Vagrant installation is the easiest method.  If you are using Ubuntu 18.04, you can install the Digital Slide Archive on your local system.

.. __methods

Installing via Docker
---------------------

This method should work on any system running Docker.  It has been tested with a variety of Ubuntu and CentOS distributions.

Prerequisites
#############

Install git, python-pip, and docker.io.  On Ubuntu, this can be done via::

    sudo apt-get update
    sudo apt-get install git docker.io python-pip

The current user needs to be a member of the docker group::

    sudo usermod -aG docker `id -u -n`

After which, you will need to log out and log back in.

Install the python docker module::

    sudo pip install docker

Get the Digital Slide Archive repository::

    git clone https://github.com/DigitalSlideArchive/digital_slide_archive

Deploy
######

::

    cd digital_slide_archive/ansible
    python deploy_docker.py start

There are many options that can be used along with the ``deploy_docker.py`` command, use ``deploy_docker.py --help`` to list them.

By default, the deployment places all database, log, and assetstore files in the ``~/.histomicstk`` directory.  The Digital Slide Archive is run on localhost at port 8080.

Update an installation
######################

::

    cd digital_slide_archive/ansible
    # Make sure you have the latest version of the deploy_docker script
    git pull
    # Make sure you have the latest docker images.
    python deploy_docker.py pull
    # stop and remove the running docker containers for the Digital Slide Archive
    python deploy_docker.py rm
    # Restart and provision the new docker containers.  Use the same
    # command-line parameters as you originally used to start the Digital Slide
    # Archive the first time.
    python deploy_docker.py start

Installing via Vagrant
----------------------

This method can work on Linux, Macintosh, or Windows.

Prerequisites
#############

Install VirtualBox, Vagrant, and git:

- Download and install git - https://git-scm.com/downloads
- Download and install virtual box - https://www.virtualbox.org/wiki/Downloads
- Download and install vagrant - https://www.vagrantup.com/downloads.html

Get the Digital Slide Archive repository::

    git clone https://github.com/DigitalSlideArchive/digital_slide_archive

Deploy
######

::

    cd digital_slide_archive
    vagrant up

The Girder instance can then be accessed at http://localhost:8009. Any image
placed in the sample_images subdirectory of the directory where 
digital_slide_archive is cloned will be seen in the TCGA collection of Girder.

The front-end UI that allows you to apply analysis modules in HistomicsTK's
docker plugins on data stored in Girder can be accessed at
http://localhost:8009/histomicsui.

You can also ssh into the vagrant virtual box using the command ``vagrant ssh``.
Digital Slide Archive and its dependencies are installed at the location
``/opt/`` (e.g., ``/opt/digital_slide_archive``).

Run tests
#########

Log in to the vagrant box::

    vagrant ssh

Inside the vagrant box, tests can be run by typing::

    cd /opt/HistomicsUI
    tox

Local installation on Ubuntu 18.04
----------------------------------

The local deployment scripts assume a reasonably plain instance of Ubuntu 18.04.

Prerequisites
#############

::

    sudo apt-get update
    sudo apt-get install -y libssl-dev git python3-dev python3-distutils python3-pip
    python3 -m pip install -U pip
    python3 -m pip install -U ansible
    git clone https://github.com/DigitalSlideArchive/digital_slide_archive

You may need to log out and log back on to ensure ansible is in your path.

Deploy
######

::

    cd digital_slide_archive/ansible
    ./deploy_local.sh

Note that if there are network issues, this deployment script does not automatically retry installation.  It may be necessary to delete partial files and run it again.
