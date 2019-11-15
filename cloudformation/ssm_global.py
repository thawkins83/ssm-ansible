import os
from troposphere import Template, iam, Ref
from awacs.aws import PolicyDocument, Statement, Action, Allow, Principal


def ssm_global():
    template = Template()

    ssm_role = iam.Role(
        'SsmRole',
        RoleName="SsmRole",
        ManagedPolicyArns=[
            "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
            "arn:aws:iam::aws:policy/AmazonS3FullAccess",
            "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
        ],
        AssumeRolePolicyDocument=PolicyDocument(
            Statement=[
                Statement(
                    Effect=Allow,
                    Action=[
                        Action("sts", "AssumeRole")
                    ],
                    Principal=Principal("Service", "ec2.amazonaws.com")
                )
            ]
        )
    )

    ssm_profile = iam.InstanceProfile(
        'SsmProfile',
        Roles=[Ref(ssm_role)],
        InstanceProfileName="SsmProfile"
    )

    template.add_resource(ssm_role)
    template.add_resource(ssm_profile)

    with open(os.path.dirname(os.path.realpath(__file__)) + '/ssm_global.yml', 'w') as cf_file:
        cf_file.write(template.to_yaml())

    return template.to_yaml()


if __name__ == '__main__':
    print(ssm_global())
