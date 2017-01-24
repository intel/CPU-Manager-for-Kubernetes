variable "instance_master_names" {
    description = "list of names used on master nodes"
    type = "list"    
}

variable "instance_etcd_names" {
    description = "list of names used on etcd nodes"
    type = "list"    
}

variable "instance_minions_names" {
    description = "list of names used on minion nodes"
    type = "list"    
}

variable "instance_master_ips" {
    description = "list of ips used on master nodes"
    type = "list"    
}

variable "instance_etcd_ips" {
    description = "list of ips used on etcd nodes"
    type = "list"    
}

variable "instance_minions_ips" {
    description = "list of ips used on minion nodes"
    type = "list"    
}

variable "instance_master_user" {
    description = "list of user used on master nodes"
    type = "list"    
}

variable "instance_etcd_user" {
    description = "list of user used on etcd nodes"
    type = "list"    
}

variable "instance_minions_user" {
    description = "list of user used on minion nodes"
    type = "list"    
}

variable "instance_master_port" {
    description = "list of port used on master nodes"
    type = "list"    
}

variable "instance_etcd_port" {
    description = "list of port used on etcd nodes"
    type = "list"    
}

variable "instance_minions_port" {
    description = "list of port used on minion nodes"
    type = "list"    
}

variable "instance_master_pk" {
    description = "list of private key used on master nodes"
    type = "list"    
}

variable "instance_etcd_pk" {
    description = "list of private key used on etcd nodes"
    type = "list"    
}

variable "instance_minions_pk" {
    description = "list of private key used on minion nodes"
    type = "list"    
}

variable "instance_master_privateip" {
    description = "list of private IPs used on master nodes"
    type = "list"    
}

variable "instance_etcd_privateip" {
    description = "list of private IPs used on etcd nodes"
    type = "list"    
}

variable "instance_minions_privateip" {
    description = "list of private IPs used on minion nodes"
    type = "list"    
}

variable "use_agent" {
    description = "use ssh agent"
    type = "string"    
}


output "count" {
    value = "${length(concat(var.instance_etcd_names, var.instance_master_names, var.instance_minions_names))}"
}

output "ip_map" {
    value = "${merge(
        zipmap(var.instance_master_names, var.instance_master_ips),
        zipmap(var.instance_etcd_names, var.instance_etcd_ips),
        zipmap(var.instance_minions_names, var.instance_minions_ips))}"
}

output "user_map" {
    value = "${merge(
        zipmap(var.instance_master_names, var.instance_master_user),
        zipmap(var.instance_etcd_names, var.instance_etcd_user),
        zipmap(var.instance_minions_names, var.instance_minions_user))}"
}

output "port_map" {
    value = "${merge(
        zipmap(var.instance_master_names, var.instance_master_port),
        zipmap(var.instance_etcd_names, var.instance_etcd_port),
        zipmap(var.instance_minions_names, var.instance_minions_port))}"
}

output "pk_map" {
    value = "${merge(
        zipmap(var.instance_master_names, var.instance_master_pk),
        zipmap(var.instance_etcd_names, var.instance_etcd_pk),
        zipmap(var.instance_minions_names, var.instance_minions_pk))}"
}

output "privateip_map" {
    value = "${merge(
        zipmap(var.instance_master_names, var.instance_master_privateip),
        zipmap(var.instance_etcd_names, var.instance_etcd_privateip),
        zipmap(var.instance_minions_names, var.instance_minions_privateip))}"
}
