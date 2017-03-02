# Configure Vagrant provider.
provider "vagrant" {
  path = "vagrant"
}

resource "vagrant_box" "box" {
  box     = "${var.box}"
  box_url = "${var.box_url}"
}

# Spawn master VMs on VirtualBox.
resource "vagrant_vbox" "vbox_master" {
  depends_on = ["vagrant_box.box"]
  cpus       = "${var.k8s_master_config["cpu"]}"
  mem        = "${var.k8s_master_config["mem"]}"

  count                  = "${length(var.k8s_masters)}"
  private_ip             = "${element(var.ips, count.index)}"
  box_name               = "${element(var.k8s_masters, count.index)}"
  box                    = "${var.box}"
  no_vbox_guest_addition = true
}

# Spawn etcd VMs on VirtualBox.
resource "vagrant_vbox" "vbox_etcd" {
  depends_on = ["vagrant_box.box"]
  cpus       = "${var.k8s_etcd_config["cpu"]}"
  mem        = "${var.k8s_etcd_config["mem"]}"

  count                  = "${length(var.k8s_etcd)}"
  private_ip             = "${element(var.ips, length(var.k8s_masters) + count.index)}"
  box_name               = "${element(var.k8s_etcd, count.index)}"
  box                    = "${var.box}"
  no_vbox_guest_addition = true
}

# Spawn minion VMs on VirtualBox.
resource "vagrant_vbox" "vbox_minions" {
  depends_on = ["vagrant_box.box"]
  cpus       = "${var.k8s_minion_config["cpu"]}"
  mem        = "${var.k8s_minion_config["mem"]}"

  count                  = "${length(var.k8s_minions)}"
  private_ip             = "${element(var.ips, length(var.k8s_masters) + length(var.k8s_etcd) + count.index)}"
  box_name               = "${element(var.k8s_minions, count.index)}"
  box                    = "${var.box}"
  no_vbox_guest_addition = true
}

# Merge VMs data into shared maps.
module "aggregator" {
  source = "../aggregator"

  instance_master_names     = ["${vagrant_vbox.vbox_master.*.box_name}"]
  instance_master_ips       = ["${vagrant_vbox.vbox_master.*.remote_ip}"]
  instance_master_user      = ["${vagrant_vbox.vbox_master.*.remote_user}"]
  instance_master_port      = ["${vagrant_vbox.vbox_master.*.remote_port}"]
  instance_master_pk        = ["${vagrant_vbox.vbox_master.*.remote_pk}"]
  instance_master_privateip = ["${vagrant_vbox.vbox_master.*.private_ip}"]

  instance_etcd_names     = ["${vagrant_vbox.vbox_etcd.*.box_name}"]
  instance_etcd_ips       = ["${vagrant_vbox.vbox_etcd.*.remote_ip}"]
  instance_etcd_user      = ["${vagrant_vbox.vbox_etcd.*.remote_user}"]
  instance_etcd_port      = ["${vagrant_vbox.vbox_etcd.*.remote_port}"]
  instance_etcd_pk        = ["${vagrant_vbox.vbox_etcd.*.remote_pk}"]
  instance_etcd_privateip = ["${vagrant_vbox.vbox_etcd.*.private_ip}"]

  instance_minions_names     = ["${vagrant_vbox.vbox_minions.*.box_name}"]
  instance_minions_ips       = ["${vagrant_vbox.vbox_minions.*.remote_ip}"]
  instance_minions_user      = ["${vagrant_vbox.vbox_minions.*.remote_user}"]
  instance_minions_port      = ["${vagrant_vbox.vbox_minions.*.remote_port}"]
  instance_minions_pk        = ["${vagrant_vbox.vbox_minions.*.remote_pk}"]
  instance_minions_privateip = ["${vagrant_vbox.vbox_minions.*.private_ip}"]

  use_agent = "${var.use_ssh_agent}"
}

# Deploy group_vars and inventory based on prepared infrastructure.
module "k8s_deploy" {
  source = "../shared"

  count = "${module.aggregator.count}"

  k8s_masters = "${var.k8s_masters}"
  k8s_etcd    = "${var.k8s_etcd}"
  k8s_minions = "${var.k8s_minions}"

  k8s_ips        = "${module.aggregator.ip_map}"
  k8s_users      = "${module.aggregator.user_map}"
  k8s_ports      = "${module.aggregator.port_map}"
  k8s_keys       = "${module.aggregator.pk_map}"
  k8s_privateips = "${module.aggregator.privateip_map}"

  k8s_use_agent = "false"
  k8s_os        = "${var.os_type}"
  k8s_names     = "${module.aggregator.names_list}"
  skip_deploy   = "${var.skip_deploy}"
}

resource "null_resource" "kargo_deployment" {
  depends_on = ["module.k8s_deploy"]

  provisioner "local-exec" {
    command = "${format("%s", var.skip_deploy == "true" ? "echo Skipping ansible provisioning" : format("../scripts/ansible_provisioner.sh %s", var.os_type))}"
  }
}
