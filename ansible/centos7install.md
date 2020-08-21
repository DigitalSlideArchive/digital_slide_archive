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
