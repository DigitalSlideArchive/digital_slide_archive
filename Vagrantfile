Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-20.04"

  # The exposed ports can be changed here; the ssh port is never necessary.
  config.vm.network "forwarded_port", guest: 22, host: 2209
  config.vm.network "forwarded_port", guest: 8080, host: 8009
  config.vm.provider "virtualbox" do |v|
    v.name = "Digital Slide Archive Ubuntu 20.04"
    # You may need to configure this to run benignly on your host machine
    v.memory = 4096
    v.cpus = 2
    config.vm.provision "shell", inline: <<-SHELL
      test -f /etc/provisioned && exit
      sudo apt-get update
      sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
      curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
      sudo apt-key fingerprint 0EBFCD88
      sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
      sudo apt-get update
      sudo apt-get install -y docker-ce git
      sudo usermod -aG docker vagrant
      sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
      sudo chmod +x /usr/local/bin/docker-compose
      docker-compose --version
      cd /home/vagrant
      git clone https://github.com/DigitalSlideArchive/digital_slide_archive.git
      cd digital_slide_archive/devops/dsa
      bash -c 'bash -c "docker-compose pull && DSA_USER=$(id -u):$(id -g) docker-compose up -d"'
      date > /etc/provisioned
    SHELL
  end
end
