output "connectivity_commands" {
  value = ["${
		formatlist("ssh %s@%s", var.user_name[0], concat(aws_instance.aws_minions.*.public_ip, aws_instance.aws_master.*.public_ip, aws_instance.aws_etcd.*.public_ip))}"]
}

output "mapped_ips" {
  value = "${module.aggregator.ip_map}"
}

output "mapped_users" {
  value = "${module.aggregator.user_map}"
}

output "mapped_ports" {
  value = "${module.aggregator.port_map}"
}

output "private_keys" {
  value = "${module.aggregator.pk_map}"
}

output "used_os" {
  value = "${var.os_type}"
}
