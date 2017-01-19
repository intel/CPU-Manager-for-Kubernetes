resource "null_resource" "master_header" {
  provisioner "local-exec" {
    command =  "echo \"[kube-master]\" > ./inventory"
  }
}

# Compone inventory: add master group.
resource "null_resource" "masters" {
  depends_on = ["null_resource.master_header"]
  count = "${length(var.k8s_masters)}"

  provisioner "local-exec" {
    command =  "echo \"${format("%s ansible_ssh_host=%s ansible_ssh_port=%s ansible_ssh_user='%s' %s ip=%s flannel_interface=%s flannel_backend_type=host-gw local_release_dir=/vagrant/temp download_run_once=False",
                                    element(var.k8s_masters, count.index),
                                    var.k8s_ips[element(var.k8s_masters, count.index)],
                                    var.k8s_ports[element(var.k8s_masters, count.index)],
                                    var.k8s_users[element(var.k8s_masters, count.index)],
                                    var.k8s_use_agent == "true" ? "" : format("ansible_ssh_private_key_file='%s'", var.k8s_keys[element(var.k8s_masters, count.index)]),
                                    var.k8s_privateips[element(var.k8s_masters, count.index)],
                                    var.k8s_privateips[element(var.k8s_masters, count.index)]
                                    )}\" >> ./inventory"
  }
}

# Compone inventory: add etcd group header.
resource "null_resource" "etcd_header" {
  depends_on = ["null_resource.masters"]
  provisioner "local-exec" {
    command =  "echo \"[etcd]\" >> ./inventory"
  }
}

# Compone inventory: add etcd group.
resource "null_resource" "etcd" {
  depends_on = ["null_resource.etcd_header"]
  count = "${length(var.k8s_etcd)}"

  provisioner "local-exec" {
    command =  "echo \"${format("%s ansible_ssh_host=%s ansible_ssh_port=%s ansible_ssh_user='%s' %s ip=%s flannel_interface=%s flannel_backend_type=host-gw local_release_dir=/vagrant/temp download_run_once=False",
                                    element(var.k8s_etcd, count.index),
                                    var.k8s_ips[element(var.k8s_etcd, count.index)],
                                    var.k8s_ports[element(var.k8s_etcd, count.index)],
                                    var.k8s_users[element(var.k8s_etcd, count.index)],
                                    var.k8s_use_agent == "true" ? "" : format("ansible_ssh_private_key_file='%s'", var.k8s_keys[element(var.k8s_etcd, count.index)]),
                                    var.k8s_privateips[element(var.k8s_etcd, count.index)],
                                    var.k8s_privateips[element(var.k8s_etcd, count.index)]
                                    )}\" >> ./inventory"
  }
}

# Compone inventory: add minion group header.
resource "null_resource" "minion_header" {
    depends_on = ["null_resource.etcd"]
    provisioner "local-exec" {
      command =  "echo \"[kube-node]\" >> ./inventory"
    }
}

# Compone inventory: add minion group.
resource "null_resource" "minions" {
  count = "${length(var.k8s_minions)}"
  depends_on = ["null_resource.minion_header"]
  provisioner "local-exec" {
    command =  "echo \"${format("%s ansible_ssh_host=%s ansible_ssh_port=%s ansible_ssh_user='%s' %s ip=%s flannel_interface=%s flannel_backend_type=host-gw local_release_dir=/vagrant/temp download_run_once=False",
                                    element(var.k8s_minions, count.index),
                                    var.k8s_ips[element(var.k8s_minions, count.index)],
                                    var.k8s_ports[element(var.k8s_minions, count.index)],
                                    var.k8s_users[element(var.k8s_minions, count.index)],
                                    var.k8s_use_agent == "true" ? "" : format("ansible_ssh_private_key_file='%s'", var.k8s_keys[element(var.k8s_minions, count.index)]),
                                    var.k8s_privateips[element(var.k8s_minions, count.index)],
                                    var.k8s_privateips[element(var.k8s_minions, count.index)]
                                    )}\" >> ./inventory"
  }
}

# Compone inventory: add k8s-cluster definition.
resource "null_resource" "children" {
  depends_on = ["null_resource.minions"]  
  provisioner "local-exec" {
    command =  "echo \"\n[k8s-cluster:children]\nkube-node\nkube-master\" >> ./inventory"
  }
}

