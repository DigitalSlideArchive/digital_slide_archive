## Installation on an AWS Centos7 image

The installation instructions are similar to ubuntu, but the Centos 7 AWS image requires slightly different package names.

I am using the "CentOS 7 (x86_64) - with Updates HVM" AMI Image, and set up a t2.large (2 CPUS/8 GBS) and added 256GB of local storage.



## Update system and install any new packages and docker

Following main docker install info from https://docs.docker.com/engine/install/centos/  

    sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo yum install epel-release
    sudo yum update -y

    sudo yum install git epel-release  docker-ce docker-ce-cli containerd.io -y
    sudo yum install python3-pip
    # Need to start the docker service
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


## If installing the NCI Seer Pediatric Pilot version of the DSA

### Install docker-compose
    sudo curl -L "https://github.com/docker/compose/releases/download/1.26.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose


    cd ~ 
    git clone https://github.com/DigitalSlideArchive/NCI-SEER-Pediatric-WSI-Pilot.git
    cd NCI-SEER-Pediatric-WSI-Pilot
    cd devops/nciseer/


