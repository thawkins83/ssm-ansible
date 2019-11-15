import os

from awacs.aws import PolicyDocument, Statement, Allow, Action, Principal
from troposphere import Template, Ref, s3, Join, iam, awslambda, GetAtt, events, Parameter
from troposphere.awslambda import Code, Environment
from troposphere.iam import Policy


def ssm_ansible():
    template = Template()
    stackname = Ref("AWS::StackName")

    template.add_parameter(Parameter(
        "LambdaZipBucket",
        Type="String",
        Description="Bucket which has Lambda Zip file",
        Default="lambda-zip-bucket",
        ConstraintDescription="Must be an existing bucket.'"
    ))

    ansible_bucket = s3.Bucket(
        'AnsibleBucket',
        BucketName=Join("", [stackname, "-code-bucket"]),
        BucketEncryption=s3.BucketEncryption(
            'AnsibleCodeBucketEncryption',
            ServerSideEncryptionConfiguration=[
                s3.ServerSideEncryptionRule(
                    ServerSideEncryptionByDefault=s3.ServerSideEncryptionByDefault(
                        'Default',
                        SSEAlgorithm='AES256'
                    )
                )
            ]
        )
    )

    ansible_lambda_role = iam.Role(
        'AnsibleLambdaRole',
        RoleName=Join("", [stackname, "-AnsibleLambdaSSM"]),
        Policies=[
            Policy(
                PolicyName="AnsibleLambdaSSM",
                PolicyDocument=PolicyDocument(
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action("ssm", "*"),
                                Action("ec2", "DescribeInstances")
                            ],
                            Resource=[
                                "*"
                            ]
                        ),
                        Statement(
                            Effect=Allow,
                            Action=[
                                Action("logs", "CreateLogGroup"),
                                Action("logs", "CreateLogStream"),
                                Action("logs", "PutLogEvents")
                            ],
                            Resource=[
                                "arn:aws:logs:*:*:*"
                            ]
                        )
                    ]
                )
            )
        ],
        AssumeRolePolicyDocument=PolicyDocument(
            Statement=[
                Statement(
                    Effect=Allow,
                    Action=[
                        Action("sts", "AssumeRole")
                    ],
                    Principal=Principal("Service", "lambda.amazonaws.com")
                )
            ]
        )
    )

    ansible_lambda = awslambda.Function(
        'AnsibleLambda',
        FunctionName=Join("", [stackname, "-ansible-ssm"]),
        Handler="lambda_function.lambda_handler",
        Runtime="python3.7",
        Role=GetAtt(ansible_lambda_role, "Arn"),
        Code=Code(
            S3Key="ansible_ssm_lambda.zip",
            S3Bucket=Ref("LambdaZipBucket")
        ),
        Environment=Environment(
            Variables={
                'code_bucket': Ref(ansible_bucket),
                'provision_playbook': "provision-playbook.yml",
                'update_playbook': "update-playbook.yml"
            }
        )
    )

    cloudwatch_event_rule_trigger_lambda = events.Rule(
        'CloudWatchEventRuleLambda',
        Description="Capture when instance stat changes to 'running' or 'terminated'.",
        EventPattern={
            "source": [
                "aws.ec2"
            ],
            "detail-type": [
                "EC2 Instance State-change Notification"
            ],
            "detail": {
                "state": [
                    "running",
                    "terminated"
                ]
            }
        },
        Name=Join("", [stackname, "-instance-state"]),
        Targets=[
            events.Target(
                'TriggerTarget',
                Arn=GetAtt(ansible_lambda, "Arn"),
                Id="TriggerTarget"
            )
        ]
    )

    cloudwatch_lambda_permission = awslambda.Permission(
        'CloudWatchLambdaPermission',
        Action="lambda:InvokeFunction",
        FunctionName=Ref(ansible_lambda),
        Principal="events.amazonaws.com",
        SourceArn=GetAtt(cloudwatch_event_rule_trigger_lambda, "Arn")
    )

    template.add_resource(ansible_bucket)
    template.add_resource(ansible_lambda_role)
    template.add_resource(ansible_lambda)
    template.add_resource(cloudwatch_event_rule_trigger_lambda)
    template.add_resource(cloudwatch_lambda_permission)

    with open(os.path.dirname(os.path.realpath(__file__)) + '/ssm_ansible.yml', 'w') as cf_file:
        cf_file.write(template.to_yaml())

    return template.to_yaml()


if __name__ == '__main__':
    print(ssm_ansible())
