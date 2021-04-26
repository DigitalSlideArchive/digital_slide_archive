Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-18.04"

  if Vagrant.has_plugin?("vagrant-cachier")
    config.cache.scope = :box
    config.cache.enable :apt
    config.cache.enable :yum
    config.cache.enable :npm
  end

  # The exposed ports can be changed here; the ssh port is never necessary.
  config.vm.network "forwarded_port", guest: 22, host: 2209
  config.vm.network "forwarded_port", guest: 8080, host: 8009
  config.vm.provider "virtualbox" do |v|
    v.name = "Digital Slide Archive Ubuntu 18.04"
    # You may need to configure this to run benignly on your host machine
    v.memory = 4096
    v.cpus = 2
    # Size the disk to a specific number of Mbytes.
    if Vagrant.has_plugin?("vagrant-disksize")
      config.disksize.size = "100GB"
      config.vm.provision "ResizeStep", type: "shell", inline: <<-SHELL
        sudo parted /dev/sda resizepart 1 100%
        sudo pvresize /dev/sda1
        sudo lvresize -rl +100%FREE /dev/mapper/vagrant--vg-root
      SHELL
    end
    config.vm.provision "AnsibleStep", type: "ansible_local" do |ansible|
      ansible.playbook = "ansible/vagrant.yml"
      ansible.extra_vars = { ansible_python_interpreter:"/usr/bin/python3" }
      ansible.galaxy_role_file = "ansible/requirements.yml"
      ansible.provisioning_path = "/vagrant"
      ansible.install_mode = "pip3"
    end
  end
end
