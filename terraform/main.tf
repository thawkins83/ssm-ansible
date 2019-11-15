locals {
  zip_path = "${path.module}/files/${var.lambda_zip}"
}

module "lambda_zip_bucket" {
  source = "./modules/bucket"
  bucket = var.lambda_zip_bucket
  region = var.region
}

resource "aws_s3_bucket_object" "ansible_ssm_lambda" {
  depends_on  = [module.lambda_zip_bucket]
  bucket      = var.lambda_zip_bucket
  key         = var.lambda_zip
  source      = local.zip_path

  etag        = filemd5(local.zip_path)
}
