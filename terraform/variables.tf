variable "aws_region" {
  description = "AWS region"
  default     = "ap-south-1"  # Mumbai
}

variable "instance_type" {
  description = "EC2 instance type"
  default     = "t3.medium"
}

variable "ami_id" {
  description = "Ubuntu 22.04 LTS AMI for ap-south-1"
  default     = "ami-0dee22c13ea7a9a67"
}

variable "key_name" {
  description = "SSH key pair name (must exist in AWS)"
  type        = string
}
