import boto3

def enable_ipv6_on_vpc(ec2_client, vpc_id):
    # Associate an IPv6 CIDR block with the VPC
    response = ec2_client.associate_vpc_cidr_block(
        VpcId=vpc_id,
        AmazonProvidedIpv6CidrBlock=True
    )
    print(f"Enabled IPv6 on VPC {vpc_id}")
    return response['Ipv6CidrBlockAssociation']['Ipv6CidrBlock']
def assign_ipv6_to_subnet(ec2_client, subnet_id, ipv6_cidr_block):
    # Associate an IPv6 CIDR block with the subnet
    response = ec2_client.associate_subnet_cidr_block(
        SubnetId=subnet_id,
        Ipv6CidrBlock=f"{ipv6_cidr_block[:-1]}::{int(subnet_id[-1], 16):x}/64"
    )
    print(f"Assigned IPv6 CIDR block to subnet {subnet_id}")
    return response['Ipv6CidrBlock']

def assign_ipv6_addresses_to_instances(ec2_client, subnet_id):
    # Describe instances in the subnet
    response = ec2_client.describe_instances(
        Filters=[
            {'Name': 'subnet-id', 'Values': [subnet_id]},
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            for network_interface in instance['NetworkInterfaces']:
                if network_interface['SubnetId'] == subnet_id:
                    # Assign an IPv6 address to the network interface
                    ec2_client.assign_ipv6_addresses(
                        NetworkInterfaceId=network_interface['NetworkInterfaceId'],
                        Ipv6AddressCount=1
                    )
                    print(f"Assigned IPv6 address to instance {instance['InstanceId']}")

def main():
    session = boto3.Session()
    ec2 = session.client('ec2')
    
    # List all AWS regions
    regions_response = ec2.describe_regions()
    #regions = [region['RegionName'] for region in regions_response['Regions']] uncomment this line
    regions = ["us-east-1"] # comment this line

    for region in regions:
        print(f"Processing region: {region}")
        ec2_client = session.client('ec2', region_name=region)

        # List all VPCs in the region
        vpcs_response = ec2_client.describe_vpcs()
        for vpc in vpcs_response['Vpcs']:
            vpc_id = vpc['VpcId']
            #if vpc_id in "vpc-08bd2cb875fa89b38":
            # Check if the VPC has IPv6 enabled
            if 'Ipv6CidrBlockAssociationSet' not in vpc or not vpc['Ipv6CidrBlockAssociationSet']:
                print(f"vpc is not assigned IPv6 {vpc['VpcId']}")
                continue  # Skip VPCs without IPv6 enabled

            # List all subnets in the VPC
            subnets_response = ec2_client.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )

            for subnet in subnets_response['Subnets']:
                subnet_id = subnet['SubnetId']
                # Check if the subnet is private and has IPv6 enabled
                route_table_response = ec2_client.describe_route_tables(
                Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_id]}]
                )
                if route_table_response['RouteTables']:
                    route_table = route_table_response['RouteTables'][0]

                    # Check if the subnet is private by looking for the absence of an internet gateway route
                    igw_route = any(route.get('GatewayId', '').startswith('igw-') for route in route_table['Routes'])
                    if igw_route :
                        continue
                    
                    # Check if the subnet is private and has IPv6 enabled
                    #if subnet['MapPublicIpOnLaunch']:
                        #continue  # Skip public subnets

                    if 'Ipv6CidrBlockAssociationSet' not in subnet or not subnet['Ipv6CidrBlockAssociationSet']:
                        print(f"Subnet is not enabled for ipv6 {subnet_id}")
                        continue  # Skip subnets without IPv6 enabled

                    # Assign IPv6 addresses to instances in the subnet
                    assign_ipv6_addresses_to_instances(ec2_client, subnet_id)

if __name__ == "__main__":
    main()
