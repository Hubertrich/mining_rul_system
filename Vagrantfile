Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"

  # Give VM its own private IP
  config.vm.network "private_network", ip: "192.168.56.10"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "4096"
    vb.cpus = 2
  end

  # Sync your project folder
  config.vm.synced_folder ".", "/vagrant"
end