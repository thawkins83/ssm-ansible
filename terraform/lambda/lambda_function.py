import boto3

import os

running = "running"
terminated = "terminated"


def lambda_handler(event, context):
    instance_id = event["detail"]["instance-id"]
    state = event["detail"]["state"]
    print("InstanceId: {}\nState: {}".format(instance_id, state))

    if state == running or state == terminated:
        client = boto3.client('ec2')
        instance = client.describe_instances(
            InstanceIds=[
                instance_id
            ],
            Filters=[
                {
                    "Name": "tag:ManagedBy",
                    "Values": [
                        "Ansible"
                    ]
                }
            ]
        )

        reservations = instance["Reservations"]
        if len(reservations) != 0:
            process_event(instance_id, state)


def process_event(instance_id, state):
    client = boto3.client('ssm')
    instance_association_name = "ansible-association-{}".format(instance_id)

    status_infos = client.describe_instance_associations_status(
        InstanceId=instance_id
    )

    association = status_infos["InstanceAssociationStatusInfos"]
    association_id = None
    if association is not None:
        for i in range(len(association)):
            if instance_association_name == association[i]["AssociationName"]:
                association_id = association[i]["AssociationId"]

    if association_id is None and state == running:
        print("Creating SSM State Manager Association: {}".format(instance_id))
        create_association(client, instance_id, instance_association_name)
    else:
        if association_id is not None:
            if state == running:
                print("Updating SSM State Manager Association: {}".format(association_id))
                update_association(client, association_id, instance_association_name)
            elif state == terminated:
                print("Deleting SSM State Manager Association: {}".format(association_id))
                delete_association(client, association_id)
        else:
            print("Association does not exist: {}".format(instance_association_name))


def delete_association(client, association_id):
    response = client.delete_association(
        AssociationId=association_id
    )
    if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
        print("AssociationId: {} was successfully deleted.".format(association_id))
    else:
        print("And error occurred while deleting the Association.")


def update_association(client, association_id, instance_association_name):
    response = client.update_association(
        AssociationId=association_id,
        AssociationName=instance_association_name,
        Parameters=ssm_params(os.environ['update_playbook'], os.environ['code_bucket'])
    )

    association_version = response["AssociationDescription"]["AssociationVersion"]
    print("AssociationId: {} update to version: {}".format(association_id, association_version))


def create_association(client, instance_id, instance_association_name):
    response = client.create_association(
        Name="AWS-ApplyAnsiblePlaybooks",
        AssociationName=instance_association_name,
        Targets=[
            {
                'Key': "InstanceIds",
                'Values': [
                    instance_id
                ]
            }
        ],
        Parameters=ssm_params(os.environ['provision_playbook'], os.environ['code_bucket'])
    )
    association_id = response["AssociationDescription"]["AssociationId"]
    print("AssociationId: {} created.".format(association_id))


def ssm_params(playbook, bucket_path):
    return {
        "Check": [
            "False"
        ],
        "ExtraVariables": [
            "SSM=True"
        ],
        "InstallDependencies": [
            "True"
        ],
        "PlaybookFile": [
            playbook
        ],
        "SourceInfo": [
            "{\n   \"path\":\"https://s3.amazonaws.com/" + bucket_path + "/\"\n}"
        ],
        "SourceType": [
            "S3"
        ],
        "Verbose": [
            "-v"
        ]
    }
