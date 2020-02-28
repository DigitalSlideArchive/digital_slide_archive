=============================
Install Digital Slide Archive
=============================

There are several ways to install the Digital Slide Archive and HistomicsUI.  If you intend to use the interface, use the Docker installation.  If you don't have docker installed, the Vagrant installation is the easiest method. 

This has been tested on systems with 4 Gb of RAM and 20 Gb of disk space, though it works better with more memory.

Installing via Docker
---------------------

This method should work on any system running Docker.  It has been tested with a variety of Ubuntu and CentOS distributions.

Prerequisites
#############

At a minimum, you need `Docker <https://docs.docker.com/install/>`_, `Python <https://www.python.org/downloads/>`_, `pip <https://pip.pypa.io/en/stable/installing/>`_.  You also need `git <https://git-scm.com/downloads>`_ or to download the installation files from the `source repository <https://github.com/DigitalSlideArchive/digital_slide_archive/tree/master/ansible>`_.

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

By default, the deployment places all database, log, and assetstore files in the ``~/.dsa`` directory.  The Digital Slide Archive is run on localhost at port 8080.

A default administrator account is created with the username ``admin`` and password ``password``.  The password can be changed after the first start, or a new administrator account with a different username can be created and the default ``admin`` user deleted.  If you change the administrator user or password, subsequent runs of ``deploy_docker.py`` will require specifying the appropriate user and password or passing the appropriate option to request the username and password on the terminal.

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

Docker and Reverse Proxy
------------------------

One common deployment is to install the Digital Slide Archive via docker and expose it as a subdirectory on another web host via a reverse proxy.  For instance, instead of having the Digital Slide Archive be reached at ``http://myserver.com:8080``, you can have it reachable at ``http://myserver.com/dsa/``.  To do this, a webserver is needed to provide the reverse proxy redirection, and some additional configuration needs to be specified as part of the provisioning of the docker containers.

Follow the guide for `Girder Reverse Proxy <https://girder.readthedocs.io/en/latest/deploy.html#reverse-proxy>`_ to configure Apache or nginx appropriately.

Create a local configuration file that can be passed to the ``deploy_docker.py`` script.  For instance, save the following as a file called ``dsa_proxy.cfg``::

    [global]
    tools.proxy.on = True

    [server]
    api_root = "/dsa/api/v1"
    static_public_path = "/dsa/static"

Now, when you issue the ``deploy_docker.py start`` command, specify the custom configuration file::

    python deploy_docker.py start --cfg=dsa_proxy.cfg

You'll need to specify the ``--cfg`` option whenever the ``start`` command used, including when updating an existing installation.

    Note:
        If you change the path of the reverse proxy on a running instance, you'll need to change the config file internal to the docker Girder container and rebuild and restart Girder within the docker.  This is in addition to restarting Apache or nginx as appropriate.
