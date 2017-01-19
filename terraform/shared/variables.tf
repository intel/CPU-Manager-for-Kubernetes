variable "count" {
    description = "number of machines to connect to"
}

variable "k8s_masters" {
  type = "list"
	description = "list of k8s master nodes"
}

variable "k8s_etcd" {
  type = "list"
	description = "list of k8s etcd nodes"
}

variable "k8s_minions" {
  type = "list"
	description = "list of k8s minion nodes"
}

variable "k8s_ips" {
	type = "map"
	description = "map of k8s IPs used in cluster"
}

variable "k8s_ports" {
	type = "map"
	description = "map of k8s ports used in cluster"
}

variable "k8s_users" {
	type = "map"
	description = "map of k8s users used in cluster"
}

variable "k8s_keys" {
	type = "map"
	description = "map of k8s private keys used in cluster"
}

variable "k8s_privateips" {
	type = "map"
	description = "map of k8s private IPs used in cluster"	
}

variable "k8s_use_agent" {
	type = "string"
	description = "true/false: use agent to connect into cluster VMs. If it's set to true k8s_keys could be melformed. (AWS will always use ssh-agent)"
}

variable "k8s_os" {
	type = "string"
	description = "operating system type used in cluster. possible values: centos, coreos, ubuntu"
}
