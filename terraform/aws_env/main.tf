# Setup provider.
provider "aws" {
  region = "${var.aws_region}"
}

# Get VPC information from remote state.
data "terraform_remote_state" "multinode_vpc" {
  backend = "s3"

  config {
    bucket = "${var.tf_bucket_name}"
    key    = "${var.vpc_state_file}"
    region = "${var.aws_region}"
  }
}

# Prepare separate subnet based on provided variables.
module "aws_subnet" {
  source = "git::ssh://git@github.com/intelsdi-x/terraform-kopernik//modules/aws_subnet"

  vpc_id      = "${data.terraform_remote_state.multinode_vpc.vpc_id}"
  vpc_cidr    = "${data.terraform_remote_state.multinode_vpc.vpc_cidr}"
  third_octet = "${var.agent_seed}"
}

# Open all ports inside private network.
resource "aws_security_group" "open_private_network" {
  vpc_id      = "${data.terraform_remote_state.multinode_vpc.vpc_id}"
  description = "open network connectivity between nodes in private network."

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["${data.terraform_remote_state.multinode_vpc.vpc_cidr}"]
  }
}

# Spawn seed VM on AWS.
resource "aws_instance" "aws_seed" {
  instance_type = "${var.seed["flavor"]}"
  ami           = "${var.seed["ami"]}"
  key_name      = "${var.aws_keyname}"

  tags {
    Name       = "seed"
    UserName   = "${var.seed["user_name"]}"
    PortNumber = "${var.seed["port_number"]}"
  }

  subnet_id              = "${module.aws_subnet.subnet_id}"
  vpc_security_group_ids = ["${module.aws_subnet.default_sg_id}", "${aws_security_group.open_private_network.id}"]
  count                  = "1"
}

# Spawn master VMs on AWS.
resource "aws_instance" "aws_master" {
  instance_type = "${var.k8s_master_config["flavor"]}"
  ami           = "${var.aws_ami}"
  key_name      = "${var.aws_keyname}"

  tags {
    Name       = "${element(var.k8s_masters, count.index)}"
    UserName   = "${element(var.user_name, count.index)}"
    PortNumber = "${element(var.port_number, count.index)}"
  }

  subnet_id              = "${module.aws_subnet.subnet_id}"
  vpc_security_group_ids = ["${module.aws_subnet.default_sg_id}", "${aws_security_group.open_private_network.id}"]
  count                  = "${length(var.k8s_masters)}"
}

# Spawn etcd VMs on AWS.
resource "aws_instance" "aws_etcd" {
  instance_type = "${var.k8s_etcd_config["flavor"]}"
  ami           = "${var.aws_ami}"
  key_name      = "${var.aws_keyname}"

  tags {
    Name       = "${element(var.k8s_etcd, count.index)}"
    UserName   = "${element(var.user_name, count.index)}"
    PortNumber = "${element(var.port_number, count.index)}"
  }

  subnet_id              = "${module.aws_subnet.subnet_id}"
  vpc_security_group_ids = ["${module.aws_subnet.default_sg_id}", "${aws_security_group.open_private_network.id}"]
  count                  = "${length(var.k8s_etcd)}"
}

# Spawn minion VMs on AWS.
resource "aws_instance" "aws_minions" {
  instance_type = "${var.k8s_minion_config["flavor"]}"
  ami           = "${var.aws_ami}"
  key_name      = "${var.aws_keyname}"

  tags {
    Name       = "${element(var.k8s_minions, count.index)}"
    UserName   = "${element(var.user_name, count.index)}"
    PortNumber = "${element(var.port_number, count.index)}"
  }

  subnet_id              = "${module.aws_subnet.subnet_id}"
  vpc_security_group_ids = ["${module.aws_subnet.default_sg_id}", "${aws_security_group.open_private_network.id}"]
  count                  = "${length(var.k8s_minions)}"
}

# Merge VMs data into shared maps.
module "aggregator" {
  source = "../aggregator"

  instance_master_names     = ["${aws_instance.aws_master.*.tags.Name}"]
  instance_master_ips       = ["${aws_instance.aws_master.*.public_ip}"]
  instance_master_user      = ["${aws_instance.aws_master.*.tags.UserName}"]
  instance_master_port      = ["${aws_instance.aws_master.*.tags.PortNumber}"]
  instance_master_pk        = ["${aws_instance.aws_master.*.tags.Name}"]
  instance_master_privateip = ["${aws_instance.aws_master.*.private_ip}"]

  instance_etcd_names     = ["${aws_instance.aws_etcd.*.tags.Name}"]
  instance_etcd_ips       = ["${aws_instance.aws_etcd.*.public_ip}"]
  instance_etcd_user      = ["${aws_instance.aws_etcd.*.tags.UserName}"]
  instance_etcd_port      = ["${aws_instance.aws_etcd.*.tags.PortNumber}"]
  instance_etcd_pk        = ["${aws_instance.aws_etcd.*.tags.Name}"]
  instance_etcd_privateip = ["${aws_instance.aws_etcd.*.private_ip}"]

  instance_minions_names     = ["${aws_instance.aws_minions.*.tags.Name}"]
  instance_minions_ips       = ["${aws_instance.aws_minions.*.public_ip}"]
  instance_minions_user      = ["${aws_instance.aws_minions.*.tags.UserName}"]
  instance_minions_port      = ["${aws_instance.aws_minions.*.tags.PortNumber}"]
  instance_minions_pk        = ["${aws_instance.aws_minions.*.tags.Name}"]
  instance_minions_privateip = ["${aws_instance.aws_minions.*.private_ip}"]

  use_agent = "true"
}

# Deploy group_vars and inventory based on prepared infrastructure.
module "k8s_deploy" {
  source = "../shared"

  count = "${length(var.k8s_masters) + length(var.k8s_minions) + length(var.k8s_etcd)}"

  k8s_masters = "${var.k8s_masters}"
  k8s_etcd    = "${var.k8s_etcd}"
  k8s_minions = "${var.k8s_minions}"

  k8s_ips        = "${module.aggregator.ip_map}"
  k8s_users      = "${module.aggregator.user_map}"
  k8s_ports      = "${module.aggregator.port_map}"
  k8s_keys       = "${module.aggregator.pk_map}"
  k8s_privateips = "${module.aggregator.privateip_map}"

  k8s_use_agent = "true"
  k8s_os        = "${var.os_type}"
}

resource "null_resource" "wait_for_connectivity" {
  count = "${length(var.k8s_masters) + length(var.k8s_minions) + length(var.k8s_etcd)}"

  provisioner "remote-exec" {
    inline = ["${format("echo %s has been spawned!", element(module.aggregator.names_list, count.index))}"]

    connection {
      type  = "ssh"
      user  = "${module.aggregator.user_map[element(module.aggregator.names_list, count.index)]}"
      host  = "${module.aggregator.ip_map[element(module.aggregator.names_list, count.index)]}"
      port  = "${module.aggregator.port_map[element(module.aggregator.names_list, count.index)]}"
      agent = "true"
    }
  }
}

resource "null_resource" "copy_inventory" {
  depends_on = ["module.k8s_deploy"]

  provisioner "local-exec" {
    command = "cp ./inventory ./../workdir/mvp_inventory/ansible_inventory"
  }
}

resource "null_resource" "deploy_seed" {
  depends_on = ["aws_instance.aws_seed", "null_resource.copy_inventory"]

  provisioner "file" {
    source      = "../../"
    destination = "."

    connection {
      type  = "ssh"
      user  = "${aws_instance.aws_seed.tags.UserName}"
      host  = "${aws_instance.aws_seed.public_ip}"
      port  = "${aws_instance.aws_seed.tags.PortNumber}"
      agent = "true"
    }
  }

  provisioner "remote-exec" {
    inline = [
      "sudo apt-get -qq update",
      "sudo apt-get -qq install -y python-pip libssl-dev",
      "sudo pip install -q ansible==2.2.0.0",
      "sudo pip install -q -r ./terraform/requirements.txt",
    ]

    connection {
      type  = "ssh"
      user  = "${aws_instance.aws_seed.tags.UserName}"
      host  = "${aws_instance.aws_seed.public_ip}"
      port  = "${aws_instance.aws_seed.tags.PortNumber}"
      agent = "true"
    }
  }
}

resource "null_resource" "kargo_deployment" {
  depends_on = ["null_resource.wait_for_connectivity", "null_resource.deploy_seed"]

  provisioner "remote-exec" {
    inline = [
      "chmod +x ./terraform/scripts/ansible_provisioner.sh",
      "./terraform/scripts/ansible_provisioner.sh \"${var.os_type}\"",
    ]

    connection {
      type  = "ssh"
      user  = "${aws_instance.aws_seed.tags.UserName}"
      host  = "${aws_instance.aws_seed.public_ip}"
      port  = "${aws_instance.aws_seed.tags.PortNumber}"
      agent = "true"
    }
  }
}
