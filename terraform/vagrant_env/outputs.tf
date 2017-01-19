output "ip_addresses" {
    value = "${module.aggregator.ip_map}"
}

output "users" {
    value = "${module.aggregator.user_map}"
}

output "ports" {
    value = "${module.aggregator.port_map}"
}

output "private_keys" {
    value = "${module.aggregator.pk_map}"
}

output "used_os" {
    value = "${var.os_type}"
}

