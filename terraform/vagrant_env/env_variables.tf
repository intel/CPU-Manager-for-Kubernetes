
variable "ips" {
  type = "list"
  description = "private ips used for internal connectivity."
  default = ["172.17.7.13","172.17.7.14","172.17.7.15","172.17.7.16"]
}

variable "box" {
  type = "string"
  description = "box name used by Vagrant to deploy VM."
  default = "ubuntu/xenial64"
}

variable "box_url" {
  type = "string"
  description = "box_url of box."
  default = ""
}
