#!/usr/bin/env python3
# Get a list of faults from a UCS Manager or standalone IMC, optionally
# by severity. This script will produce no output if there are no faults.

import argparse
import configparser
import os
import socket

from ucsmsdk.ucshandle import UcsHandle
from imcsdk.imchandle import ImcHandle

# You can change this default location to one more suitable to your
# environment, or else override it with the --config option.
default_ini = '/etc/ucs_credentials.ini'

allowed_severities = ['critical', 'major', 'minor', 'warning', 'info']

# Read the CLI arguments
parser = argparse.ArgumentParser(
    description="Get a list of current UCS device faults.")

parser.add_argument(
    '--config', type=str, default=default_ini,
    help=("Optional location of configuration file containing UCS "
          "credentials. (Default: {})").format(default_ini))
parser.add_argument(
    '--severity', type=str,
    help=("Optional severity level to use as a filter. One of: {}".format(
        allowed_severities)))
parser.add_argument(
    '--type', type=str,
    help=("Host type ('ucsm' or 'imc'). Required unless provided in "
          "the configuration file."))
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
    args.severity = args.severity.lower()
    if args.severity not in allowed_severities:
        print('Unexpected severity "{}". Should be one of: {}'.format(
            args.severity, allowed_severities))
        exit(1)

# Verify that the UCS hostname or IP address is valid
try:
    socket.gethostbyname(args.ucs_host)
except:
    print('There was a problem validating the UCS hostname or IP address:'
          '({})'.format(args.ucs_host))
    exit(1)

# Read the data from the INI file for this host
cp = configparser.ConfigParser()
cp.read(args.config)

if args.ucs_host not in cp:
    print('Error: UCS host ({}) does not exist in the config file ({})'.format(
        args.ucs_host, args.config))
    exit(1)

# Get the login credentials for the host, or else use defaults if available
username = cp[args.ucs_host].get('username', cp['DEFAULT'].get('username'))
password = cp[args.ucs_host].get('password', cp['DEFAULT'].get('password'))
server_type = args.type or cp[args.ucs_host].get('type', cp['DEFAULT'].get('type'))

if server_type is None:
    print('Error: Host type is not defined for {} in {}. '
          'You must update that configuration file or pass in a --type '
          'argument. Expected values: "ucsm" or "imc"'.format(args.ucs_host,
                                                              args.config))
    exit(1)

if username is None:
    print("No username found for host {} and no default".format(args.ucs_host))
    exit(1)

if password is None:
    print("No password found for host {} and no default".format(args.ucs_host))
    exit(1)

if type is None:
    print("No host type was provided in the command line or in the"
          "configuration file. It should be either 'ucsm' or 'imc'.")
    exit(1)

if server_type == 'ucsm':
    handle = UcsHandle(args.ucs_host, username, password)
    if not handle.login():
        print("Failed to connect to {} as user {}!".format(args.ucs_host,
                                                           username))
        exit(1)

    if args.severity is not None:
        # Build a filter string that we will pass into an API call (UCSM only)
        filter_str = '(severity, "{}", type="eq")'.format(args.severity)
    else:
        filter_str = None

    # Output the list of faults, if any, with the given severity level
    fault_list = handle.query_classid('faultInst', filter_str=filter_str)
    for fault in fault_list:
        print('{}: [{}] {}: {}'.format(fault.created, fault.severity,
                                       fault.cause, fault.descr))
    handle.logout()

elif server_type == 'imc':
    handle = ImcHandle(args.ucs_host, username, password)
    if not handle.login():
        print("Failed to connect to {} as user {}!".format(args.ucs_host,
                                                           username))
        exit(1)

    # Output the list of faults, if any, with the given severity level
    fault_list = handle.query_classid('faultInst')
    for fault in fault_list:
        if args.severity is None or args.severity == fault.severity:
            print('{}: [{}] {}: {}'.format(fault.created, fault.severity,
                                           fault.cause, fault.descr))
    handle.logout()

else:
    print("Unrecognized server type '{}'. "
          "It should be 'ucsm' or 'imc'.".format(server_type))
    exit(1)


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
