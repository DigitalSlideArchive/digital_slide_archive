## Installation on an AWS Centos7 image

The installation instructions are similar to ubuntu, but the Centos 7 AWS image requires slightly different package names.

## Update system and install any new packages and docker

Following main docker install info from https://docs.docker.com/engine/install/centos/  

    sudo yum update
    sudo yum upgrade -y
    sudo yum install git

    sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo yum install docker-ce docker-ce-cli containerd.io -y
    sudo systemctl start docker



The current user needs to be a member of the docker group:

    sudo usermod -aG docker `id -u -n`

After which, you will need re-evaluate group membership:

    newgrp docker

Double check which version of pip is installed; Ubuntu 18.04 still defaults to pip version 9.0.1 which is quite old.

   pip --version
   
If your version is older than 19.0, upgrade pip to a more recent version

   sudo pip install --upgrade pip

### Can install pip either for the whole system or for your local user account
    pip install --upgrade pip --user

