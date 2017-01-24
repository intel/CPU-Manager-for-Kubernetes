variable "user_name" {
  description = "User name required for ssh access."
  default     = ["ubuntu"]
}

variable "port_number" {
  description = "Port which provides SSH access."
  default     = ["22"]
}

variable "aws_ami" {
  description = "AWS ami used for booting VM."
  default     = "ami-9dcfdb8a"
}

variable "seed" {
  default = {
    ami         = "ami-9dcfdb8a"
    flavor      = "m4.large"
    user_name   = "ubuntu"
    port_number = "22"
  }
}

variable "aws_keyname" {
  default = "snapbot-private"
}

# Don't change following parameters.
variable "aws_region" {
  default = "us-east-1"
}

variable agent_seed {}

variable "tf_bucket_name" {
  default = "terraform-statefiles"
}

variable "vpc_state_file" {
  default = "multinode_vpc/terraform.tfstate"
}
