
Install pip packages

```shell script
$ python -m pip install troposphere
$ python -m pip install awacs
```

Run troposphere files to generate cfn templates

```shell script
$ python ssm_global.py
$ python ssm_network.py
$ python ssm_ansible.py
```

Create stack that creates global entities (IAM) and protect it from deletion

```shell script
$ aws cloudformation deploy --stack-name ssm-global --template-file ssm_global.yml --capabilities CAPABILITY_NAMED_IAM
$ aws cloudformation update-termination-protection --stack-name ssm-global --enable-termination-protection
```

Create stack for network and protect it from deletion

```shell script
$ aws cloudformation deploy --stack-name ssm-network --template-file ssm_network.yml
$ aws cloudformation update-termination-protection --stack-name ssm-network --enable-termination-protection
```

In an effort to save money, VPC Endpoints and NAT Gateways can be started/stopped when not needed, default is disabled (above)

```shell script
$ aws cloudformation deploy --stack-name ssm-network --template-file ssm_network.yml --parameter-overrides CreateEndpoints=Yes CreateNatGateway=Yes
```

or 

```shell script
$ aws cloudformation deploy --stack-name ssm-network --template-file ssm_network.yml --parameter-overrides CreateEndpoints=No CreateNatGateway=No
```

Create stack where all the magic occurs

```shell script
$ aws cloudformation deploy --stack-name ssm-ansible --template-file ssm_ansible.yml --capabilities CAPABILITY_NAMED_IAM --parameter-overrides LambdaZipBucket=<YOUR_BUCKET_NAME>
```
