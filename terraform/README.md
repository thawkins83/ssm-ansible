If you would like to use S3 Backend for Terraform, edit the `vars/backend-config.tfvars` file accordingly, then run the following command.  

```shell script
$ terraform init -backend-config=vars/backend-config.tfvars
```

Otherwise, run
```shell script
$ terraform init
```

Edit the `vars/blog.tfvars` file with appropriate values and run the follow command.

```shell script
$ terraform apply -var-file=vars/prod.tfvars
```