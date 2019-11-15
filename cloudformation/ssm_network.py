import os

from troposphere import Template, ec2, Tags, GetAtt, Cidr, Ref, Select, GetAZs, Join, Parameter, Output, Export, \
    Equals, Or, Condition


def ssm_network():
    template = Template()

    default_route = "0.0.0.0/0"
    vpc_cidr = "192.168.0.0/16"

    template.add_parameter(Parameter(
        "VpcCidr",
        Type="String",
        Description="Cidr block for VPC",
        MinLength="9",
        MaxLength="18",
        Default=vpc_cidr,
        AllowedPattern="(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/(\\d{1,2})",
        ConstraintDescription="Must match following pattern 'xxx.xxx.xxx.xxx/xx'"
    ))

    template.add_parameter(Parameter(
        "CreateEndpoints",
        Type="String",
        Description="Create VPC Endpoints",
        Default="No",
        AllowedValues=["Yes", "No"],
        ConstraintDescription="'Yes' or 'No' are only options"
    ))

    template.add_parameter(Parameter(
        "CreateNatGateway",
        Type="String",
        Description="Create NAT Gateway",
        Default="No",
        AllowedValues=["Yes", "No"],
        ConstraintDescription="'Yes' or 'No' are only options"
    ))

    conditions = {
        "CreateVpcEndpointsUpperYes": Equals(
            Ref("CreateEndpoints"), "Yes"
        ),
        "CreateVpcEndpointsLowerYes": Equals(
            Ref("CreateEndpoints"), "yes"
        ),
        "CreateVpcEndpoints": Or(
            Condition("CreateVpcEndpointsUpperYes"),
            Condition("CreateVpcEndpointsLowerYes")
        ),
        "CreateNatGatewayUpperYes": Equals(
            Ref("CreateNatGateway"), "Yes"
        ),
        "CreateNatGatewayLowerYes": Equals(
            Ref("CreateNatGateway"), "yes"
        ),
        "CreateNatGateway": Or(
            Condition("CreateNatGatewayUpperYes"),
            Condition("CreateNatGatewayLowerYes")
        )
    }

    ssm_vpc = ec2.VPC(
        'SsmVpc',
        CidrBlock=Ref("VpcCidr"),
        InstanceTenancy="default",
        EnableDnsHostnames=True,
        EnableDnsSupport=True,
        Tags=Tags(
            Name="SSM VPC"
        )
    )

    subnet_blocks = Cidr(GetAtt(ssm_vpc, "CidrBlock"), 256, 8)

    ssm_ig = ec2.InternetGateway(
        'SsmIG',
    )

    ssm_attach_gw = ec2.VPCGatewayAttachment(
        'SsmAttachGateway',
        InternetGatewayId=Ref(ssm_ig),
        VpcId=Ref(ssm_vpc)
    )

    ssm_public_subnet = ec2.Subnet(
        'SsmPublicSubnet',
        DependsOn=ssm_attach_gw,
        AvailabilityZone=Select(0, GetAZs('')),
        CidrBlock=Select(0, subnet_blocks),
        VpcId=Ref(ssm_vpc),
        Tags=Tags(
            Name="Public Subnet"
        )
    )

    ssm_public_route_table = ec2.RouteTable(
        'SsmPublicRouteTable',
        VpcId=Ref(ssm_vpc),
    )

    ssm_public_route = ec2.Route(
        'SsmPublicRoute',
        DestinationCidrBlock=default_route,
        GatewayId=Ref(ssm_ig),
        RouteTableId=Ref(ssm_public_route_table)
    )

    ssm_public_subnet_route_table_association = ec2.SubnetRouteTableAssociation(
        'SsmPublicSubnetRouteTableAssociation',
        RouteTableId=Ref(ssm_public_route_table),
        SubnetId=Ref(ssm_public_subnet)
    )

    ssm_eip_nat_gateway = ec2.EIP(
        'SsmEipNatGateway',
        Condition="CreateNatGateway"
    )

    ssm_nat_gateway = ec2.NatGateway(
        'SsmNatGateway',
        Condition="CreateNatGateway",
        DependsOn=ssm_eip_nat_gateway,
        SubnetId=Ref(ssm_public_subnet),
        AllocationId=GetAtt(ssm_eip_nat_gateway, "AllocationId"),
    )

    ssm_private_subnet = ec2.Subnet(
        'SsmPrivateSubnet',
        DependsOn=ssm_attach_gw,
        AvailabilityZone=Select(0, GetAZs('')),
        CidrBlock=Select(1, subnet_blocks),
        VpcId=Ref(ssm_vpc),
        Tags=Tags(
            Name="Private Subnet"
        )
    )

    ssm_private_route_table = ec2.RouteTable(
        'SsmPrivateRouteTable',
        VpcId=Ref(ssm_vpc),
    )

    ssm_private_route = ec2.Route(
        'SsmPrivateRoute',
        Condition="CreateNatGateway",
        DestinationCidrBlock=default_route,
        NatGatewayId=Ref(ssm_nat_gateway),
        RouteTableId=Ref(ssm_private_route_table)
    )

    ssm_private_subnet_route_table_association = ec2.SubnetRouteTableAssociation(
        'SsmPrivateSubnetRouteTableAssociation',
        RouteTableId=Ref(ssm_private_route_table),
        SubnetId=Ref(ssm_private_subnet)
    )

    ssm_sg_ingress_rules = [
        ec2.SecurityGroupRule(
            ToPort=443,
            FromPort=443,
            IpProtocol="tcp",
            CidrIp=GetAtt(ssm_vpc, "CidrBlock")
        )
    ]

    ssm_security_group = ec2.SecurityGroup(
        'SsmSecurityGroup',
        GroupName="SsmSG",
        GroupDescription="SG for SSM usage",
        VpcId=Ref(ssm_vpc),
        SecurityGroupIngress=ssm_sg_ingress_rules
    )

    ssm_s3e_vpc_endpoint = ec2.VPCEndpoint(
        'SsmS3VpcEndpoint',
        Condition="CreateVpcEndpoints",
        RouteTableIds=[
            Ref(ssm_private_route_table)
        ],
        ServiceName=vpc_endpoint("s3"),
        VpcId=Ref(ssm_vpc),
        VpcEndpointType="Gateway"
    )

    ssm_ssm_vpc_endpoint = ec2.VPCEndpoint(
        'SsmSsmVpcEndpoint',
        Condition="CreateVpcEndpoints",
        SubnetIds=[Ref(ssm_private_subnet)],
        ServiceName=vpc_endpoint("ssm"),
        VpcId=Ref(ssm_vpc),
        VpcEndpointType="Interface",
        SecurityGroupIds=[
            Ref(ssm_security_group)
        ],
        PrivateDnsEnabled=True
    )

    ssm_ssmmessages_vpc_endpoint = ec2.VPCEndpoint(
        'SsmSsmMessagesVpcEndpoint',
        Condition="CreateVpcEndpoints",
        SubnetIds=[Ref(ssm_private_subnet)],
        ServiceName=vpc_endpoint("ssmmessages"),
        VpcId=Ref(ssm_vpc),
        VpcEndpointType="Interface",
        SecurityGroupIds=[
            Ref(ssm_security_group)
        ],
        PrivateDnsEnabled=True
    )

    ssm_ec2messages_vpc_endpoint = ec2.VPCEndpoint(
        'SsmEc2MessagesVpcEndpoint',
        Condition="CreateVpcEndpoints",
        SubnetIds=[Ref(ssm_private_subnet)],
        ServiceName=vpc_endpoint("ec2messages"),
        VpcId=Ref(ssm_vpc),
        VpcEndpointType="Interface",
        SecurityGroupIds=[
            Ref(ssm_security_group)
        ],
        PrivateDnsEnabled=True
    )

    template.add_resource(ssm_vpc)
    template.add_resource(ssm_ig)
    template.add_resource(ssm_attach_gw)
    template.add_resource(ssm_eip_nat_gateway)
    template.add_resource(ssm_public_subnet)
    template.add_resource(ssm_public_route_table)
    template.add_resource(ssm_nat_gateway)
    template.add_resource(ssm_public_route)
    template.add_resource(ssm_public_subnet_route_table_association)
    template.add_resource(ssm_private_subnet)
    template.add_resource(ssm_private_route_table)
    template.add_resource(ssm_private_route)
    template.add_resource(ssm_private_subnet_route_table_association)
    template.add_resource(ssm_security_group)
    template.add_resource(ssm_s3e_vpc_endpoint)
    template.add_resource(ssm_ec2messages_vpc_endpoint)
    template.add_resource(ssm_ssm_vpc_endpoint)
    template.add_resource(ssm_ssmmessages_vpc_endpoint)

    for k in conditions:
        template.add_condition(k, conditions[k])

    template.add_output(Output(
        'SsmVpc',
        Description="VPC for SSM",
        Value=Ref(ssm_vpc),
        Export=Export(Join("", [Ref("AWS::StackName"), "-ssm-vpc"]))
    ))

    template.add_output(Output(
        'SsmSg',
        Description="Security Group for SSM",
        Value=Ref(ssm_security_group),
        Export=Export(Join("", [Ref("AWS::StackName"), "-ssm-sg"]))
    ))

    template.add_output(Output(
        'SsmPrivateSubnet',
        Description="Private Subnet for SSM",
        Value=Ref(ssm_private_subnet),
        Export=Export(Join("", [Ref("AWS::StackName"), "-ssm-private-subnet"]))
    ))

    template.add_output(Output(
        'SsmPrivateRouteTable',
        Description="Private RouteTable for SSM",
        Value=Ref(ssm_private_route_table),
        Export=Export(Join("", [Ref("AWS::StackName"), "-ssm-private-route-table"]))
    ))

    with open(os.path.dirname(os.path.realpath(__file__)) + '/ssm_network.yml', 'w') as cf_file:
        cf_file.write(template.to_yaml())

    return template.to_yaml()


def vpc_endpoint(service):
    return Join(".", ["com", "amazonaws", Ref("AWS::Region"), service])


if __name__ == '__main__':
    print(ssm_network())
