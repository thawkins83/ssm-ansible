variable "region" {
  default = "us-east-1"
}

variable "profile" {}
variable "lambda_zip_bucket" {}
variable "lambda_zip" {
  default = "ansible_ssm_lambda.zip"
}