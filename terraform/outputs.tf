output "instance_public_ip" {
  value       = aws_eip.teacher_rag_ip.public_ip
  description = "Public IP address of the EC2 instance"
}

output "instance_id" {
  value       = aws_instance.teacher_rag.id
  description = "EC2 Instance ID"
}

output "security_group_id" {
  value       = aws_security_group.teacher_rag_sg.id
  description = "Security Group ID"
}

output "ssh_command" {
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_eip.teacher_rag_ip.public_ip}"
  description = "Command to SSH into the instance"
}

output "app_url" {
  value       = "http://${aws_eip.teacher_rag_ip.public_ip}:3000"
  description = "Application URL"
}

output "api_url" {
  value       = "http://${aws_eip.teacher_rag_ip.public_ip}:8000"
  description = "API URL"
}
