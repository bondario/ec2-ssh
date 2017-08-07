from __future__ import print_function

import argparse
import os
import random
import sys

import boto3

__version__ = '1.8.0'

parser = argparse.ArgumentParser(
    description="""
    SSH into an ec2 host where <tag-value> matches a tag which defaults to
    'Name' or environment variable EC2_HOST_TAG. In the case there is more than
    one such instance, one will be chosen at random. 'username' defaults to
    ubuntu.  A small bashrc file is added over ssh to give a nice prompt. Any
    extra arguments at the end are passed to ssh directly.
    """
)
parser.add_argument('-t', '--tag', type=str,
                    default=os.getenv('EC2_HOST_TAG', 'Name'),
                    help="Tag to match, defaults to 'Name'")
parser.add_argument('-u', '--user', type=str,
                    default=os.getenv('EC2_SSH_USER', 'ubuntu'),
                    help="Which user to connect with, defaults to 'ubuntu'")
parser.add_argument('value', help="The value for the tag to match")


def main():
    args, unparsed = parser.parse_known_args()

    if '@' in args.value:
        username, value = args.value.split('@', 1)
    else:
        username = args.user
        value = args.value

    host_name = get_host_name(args.tag, value)

    if not host_name:
        print("ec2-ssh: no hosts matched", file=sys.stderr)
        sys.exit(1)

    command = [
        'ssh',
        '-t', '-t',
        username + '@' + host_name,
    ]
    if unparsed:
        command.extend(unparsed)

    print("ec2-ssh connecting to {}".format(host_name), file=sys.stderr)
    sys.stdout.flush()
    os.execlp(*command)


def get_host_name(tag, value):
    instances = get_instances(tag, value)
    for instance_id in instances:
        return instances[instance_id]['public']


def ec2_host_parser():
    parser = argparse.ArgumentParser(
        description="Output ec2 public host names for active hosts in random "
                    "order, optionally match a tag which defaults to 'Name' "
                    "or environment variable EC2_HOST_TAG."
    )
    parser.add_argument('value', type=str, nargs='?',
                        help='the value the tag should equal')
    parser.add_argument('-t', '--tag', type=str,
                        default=os.getenv('EC2_HOST_TAG', 'Name'),
                        help='which tag to search')
    return parser


def host():
    args = ec2_host_parser().parse_args()
    instances = get_instances(args.tag, args.value)
    for instance_id in instances:
        print('{}\t{}\t{}\t{}\t{}'.format(
            instances[instance_id]['type'],
            instances[instance_id]['az'],
            instances[instance_id]['public'],
            instances[instance_id]['private'],
            instances[instance_id]['name'],
        ))


def get_instances(tag, value):
    conn = boto3.client('ec2')

    filters = []
    if value:
        filters.append({
            'Name': 'tag:' + tag,
            'Values': [value]
        })

    data = conn.describe_instances(Filters=filters)

    instances = {}
    for reservation in data['Reservations']:
        for i in reservation['Instances']:
            if i['State']['Name'] not in ('running'):
                continue
            instances[i['InstanceId']] = {}
            if i['PublicIpAddress']:
                instances[i['InstanceId']]['public'] = i['PublicIpAddress']
            if i['PrivateIpAddress']:
                instances[i['InstanceId']]['private'] = i['PrivateIpAddress']
            if i['InstanceType']:
                instances[i['InstanceId']]['type'] = i['InstanceType']
            if i['Placement']['AvailabilityZone']:
                instances[i['InstanceId']]['az'] = i['Placement']['AvailabilityZone']
            if i['Tags']:
                for tag in i['Tags']:
                    if tag['Key'] == 'Name':
                        instances[i['InstanceId']]['name'] = tag['Value']
    return instances


if __name__ == '__main__':
    main()
