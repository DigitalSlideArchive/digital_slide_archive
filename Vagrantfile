# Required for Ansible Galaxy
Vagrant.require_version ">=1.8.0"

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/trusty64"

  config.vm.hostname = "digital-slide-archive.dev"

  # config.vm.network "forwarded_port", guest: 80, host: 8080
  PRIVATE_IP = "172.28.125.100"
  config.vm.network "private_network", ip: PRIVATE_IP
  # config.vm.network "private_network", type: "dhcp"
  config.vm.post_up_message = "Web server is running at http://#{PRIVATE_IP}"

  config.vm.synced_folder ".", "/vagrant", disabled: true
  config.vm.synced_folder ".", "/home/vagrant/digital_slide_archive"

  provisioner_type = if
      Gem::Version.new(Vagrant::VERSION) > Gem::Version.new('1.8.1')
    then
      # Vagrant > 1.8.1 is required due to
      # https://github.com/mitchellh/vagrant/issues/6793
      "ansible_local"
    else
      "ansible"
    end
  config.vm.provision provisioner_type do |ansible|
    ansible.playbook = "ansible/vagrant-playbook.yml"
    ansible.galaxy_role_file = "ansible/requirements.yml"
    if provisioner_type == "ansible_local"
      ansible.provisioning_path = "/home/vagrant/digital_slide_archive"
    end
  end

  config.vm.provider "virtualbox" do |virtualbox|
    virtualbox.name = "digital-slide-archive.dev"
    virtualbox.memory = 1024
  end

  config.ssh.forward_agent = true
  config.ssh.forward_x11 = true
end
