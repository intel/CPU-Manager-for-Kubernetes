variable "use_ssh_agent" {
  type    = "string"
  default = "false"
  description = "use_ssh_agent use ssh agent or not for connectivity into cluster."
}

variable "os_type" {
  type    = "string"
  default = "ubuntu"
  description = "available OSes: ubuntu, centos, coreos."
}

variable "k8s_masters" {
  type = "list"
  default = ["k8s-m1"]
  description = "list of master nodes. IMPORTANT WARNING: please be informed that hostname can contain only alpha-numerical characters or \"-\"."
}

variable "k8s_etcd" {
  type = "list"
  default = ["k8s-e1"]
  description = "list of etcd nodes. IMPORTANT WARNING: please be informed that hostname can contain only alpha-numerical characters or \"-\"."
}

variable "k8s_minions" {
  type = "list"
  default = ["k8s-c1", "k8s-c2"]
  description = "list of minion nodes. IMPORTANT WARNING: please be informed that hostname can contain only alpha-numerical characters or \"-\"."
}


# [VirtualBox] cpu - number of virtual cores for VM.
# [VirtualBox] mem - number of RAM for VM.
# [AWS] flavor - valid name of AWS flavor.
variable "k8s_master_config" {
  type = "map"
  description = "master nodes configuration."
  default = {
    cpu = "2"
    mem = "2048"
    flavor = "m4.large"
  }
}

variable "k8s_etcd_config" {
  type = "map"
  description = "etcd nodes configuration."
  default = {
    cpu = "2"
    mem = "2048"
    flavor = "m4.large"
  }
}

variable "k8s_minion_config" {
  type = "map"
  description = "minion nodes configuration."
  default = {
    cpu = "4"
    mem = "2048"
    flavor = "m4.4xlarge"
  }
}
