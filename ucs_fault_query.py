#!/usr/bin/env python3
# Get a list of current UCS device faults, optionally by severity.

import argparse
import configparser
import os
import socket

from ucsmsdk.ucshandle import UcsHandle

allowed_severities = ['critical', 'major', 'minor', 'warning', 'info']
default_ini = '/etc/ucsm_credentials.ini'
config_help = (
    "(Optional) Location of configuration file containing UCS credentials. "
    "(Default: {})").format(default_ini)
severity_help = "(Optional) Severity level to use as a filter. {}".format(
    allowed_severities)

# Read the CLI arguments
parser = argparse.ArgumentParser(
    description="Get a list of current UCS device faults.")
parser.add_argument('--config', type=str, default=default_ini,
                    help=config_help)
parser.add_argument('--severity', type=str, help=severity_help)
parser.add_argument('ucs_host', type=str,
                    help="IP address or hostname of the UCS device.")
args = parser.parse_args()

# Make sure that the configuration file exists
if not os.path.isfile(args.config):
    print('Configuration file {} does not exist!'.format(args.config))
    exit(1)

# Is the file readable?
if not os.access(args.config, os.R_OK):
    print('Configuration file {} is not readable!'.format(args.config))
    exit(1)

# Make sure that the user provided a valid fault severity level
if args.severity is not None:
    severity = args.severity.lower()
    if severity not in allowed_severities:
        print('Unexpected severity "{}". Should be one of: {}'.format(
            severity, allowed_severities))
        exit(1)
    filter_str = '(severity, "{}", type="eq")'.format(severity)
else:
    filter_str = None

# Verify that the UCS hostname or IP address is valid
try:
    socket.gethostbyname(args.ucs_host)
except UnicodeError:
    print('There was a problem resolving the UCS hostname or IP address:'
          '({})'.format(args.ucs_host))
    exit(1)

# Get the login credentials for the host, or else use defaults
cp = configparser.ConfigParser()
cp.read(args.config)
config = cp[args.ucs_host] if args.ucs_host in cp.sections() else cp['DEFAULT']

# Create a connection handle
handle = UcsHandle(args.ucs_host, config['username'], config['password'])

# Login to the server
if not handle.login():
    print("Failed to connect to {} as user {}!".format(args.ucs_host,
                                                       config['username']))
    exit(1)

fault_list = handle.query_classid('faultInst', filter_str=filter_str)

# Logout from the server
handle.logout()

# Output the list of faults, if any, with the given severity level
for fault in fault_list:
    print('{}: [{}] {}: {}'.format(fault.created, fault.severity, fault.cause,
                                   fault.descr))

# Here is a full list of attributes available to the fault object
#   code
#   ack
#   cause
#   change_set
#   child_action
#   created
#   descr
#   highest_severity
#   id
#   last_transition
#   lc
#   occur
#   orig_severity
#   prev_severity
#   rule
#   sacl
#   severity
#   status
#   tags
#   type