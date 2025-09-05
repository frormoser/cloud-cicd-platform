variable "project_name" {
  type    = string
  default = "cloud-cicd-platform"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "vpc_cidr" {
  type    = string
  default = "10.10.0.0/16"
}

variable "public_subnet_cidr" {
  type    = string
  default = "10.10.1.0/24"
}

variable "key_pair_name" {
  description = "Name of the existing AWS key pair to use for SSH access"
  type        = string
}

variable "instance_type" {
  type    = string
  default = "t2.micro"
}

variable "enable_eks" {
  description = "Enable EKS"
  type        = bool
  default     = false
}

variable "enable_documentdb" {
  description = "Enable DocumentDB"
  type        = bool
  default     = false
}

variable "tags" {
  type = map(string)
  default = {
    Owner      = "Federico Rormoser"
    Project    = "Cloud-CI-CD-Platform"
    ManagedBy  = "Terraform"
    CostCenter = "demo"
    Env        = "dev"
  }
}
