data "aws_ami" "amzn2" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
  filter {
    name   = "state"
    values = ["available"]
  }
}

resource "aws_security_group" "jenkins" {
  name        = "${var.project_name}-jenkins-sg"
  description = "Allow SSH, HTTP and Jenkins"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Jenkins"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.project_name}-jenkins-sg" })
}

resource "aws_instance" "jenkins" {
  ami                    = data.aws_ami.amzn2.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.jenkins.id]
  key_name               = var.key_pair_name
  associate_public_ip_address = true

  user_data = <<-EOF
  #!/bin/bash
  set -eux

  amazon-linux-extras install docker -y || yum install -y docker
  systemctl enable docker
  systemctl start docker
  usermod -aG docker ec2-user

  # Git
  yum install -y git

  # Jenkins in Docker
  mkdir -p /var/jenkins_home
  chown -R 1000:1000 /var/jenkins_home

  docker run -d --restart=always --name jenkins \
    -p 8080:8080 -p 50000:50000 \
    -v /var/jenkins_home:/var/jenkins_home \
    jenkins/jenkins:lts-jdk17

  # kubectl
  curl -sSLo /usr/local/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/$(curl -sS https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
  chmod +x /usr/local/bin/kubectl

  # Helm
  curl -sSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

  echo "Jenkins initial password at /var/jenkins_home/secrets/initialAdminPassword" > /etc/motd
  EOF

  tags = merge(var.tags, { Name = "${var.project_name}-jenkins" })
}
