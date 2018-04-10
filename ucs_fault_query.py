#!/usr/bin/env python3
# Get a list of faults from a UCS Manager or standalone IMC, optionally
# by severity. This script will produce no output if there are no faults.

import argparse
import configparser
import os
import re
import socket

from ucsmsdk.ucshandle import UcsHandle
from imcsdk.imchandle import ImcHandle

allowed_severities = ['critical', 'major', 'minor', 'warning', 'info']
# You can change this default location to one more suitable to your
# environment, or else override it with the --config option.
default_ini = '/etc/ucs_credentials.ini'


def get_args():
    """Parse the the CLI arguments"""
    parser = argparse.ArgumentParser(
        description="Get a list of current UCS device faults.")

    parser.add_argument(
        '--config', type=str, default=default_ini,
        help=("Optional location of configuration file containing UCS "
              "credentials. (Default: {})").format(default_ini))
    parser.add_argument(
        '--severity', type=str, choices=allowed_severities,
        help="Optional severity level to use as a filter")
    parser.add_argument(
        '--type', type=str,
        help=("Host type ('ucsm' or 'imc'). Required unless provided in "
              "the configuration file."))
    parser.add_argument('ucs_host', type=str,
                        help="Name or IP address of the UCS device.")
    parser.add_argument(
        'alt_address', nargs='*',
        help='Space delimited list of alternate hostnames/addresses to try')

    args = parser.parse_args()

    # Make sure that the configuration file exists
    if not os.path.isfile(args.config):
        print('Configuration file {} does not exist!'.format(args.config))
        exit(1)

    # Is the file readable?
    if not os.access(args.config, os.R_OK):
        print('Configuration file {} is not readable!'.format(args.config))
        exit(1)

    return args


def get_device_parameters(args):
    """Get the device parameters needed to connect to the device

    Uses CLI options, config file values, and defaults. Exits with an error
    message if there is a problem.

    Returns:
        dict
    """
    params = {}

    # Read the data from the INI file for this host
    cp = configparser.ConfigParser()
    cp.read(args.config)

    if args.ucs_host not in cp:
        print('Error: UCS host ({}) does not exist in the config file '
              '({})'.format(args.ucs_host, args.config))
        exit(1)

    # Get the login credentials for the host, or else use defaults if available
    config_host = cp[args.ucs_host]
    config_default = cp['DEFAULT']

    params['username'] = config_host.get(
        'username', config_default.get('username'))
    params['password'] = config_host.get(
        'password', config_default.get('password'))
    params['server_type'] = args.type or config_host.get(
        'type', config_default.get('type'))

    config_addresses = parse_config_addresses(config_host.get('addresses', ''))
    params['alternate_addresses'] = args.alt_address or config_addresses

    if params['server_type'] is None:
        print('Error: Host type is not defined for {} in {}. '
              'You must update that configuration file or pass in a --type '
              'argument. Expected values: "ucsm" or "imc"'.format(
               args.ucs_host, args.config))
        exit(1)

    if params['username'] is None:
        print("No username found for host {} and no default".format(
            args.ucs_host))
        exit(1)

    if params['password'] is None:
        print("No password found for host {} and no default".format(
            args.ucs_host))
        exit(1)

    return params


def parse_config_addresses(config_value):
    if config_value.strip():
        return re.split('\s+', config_value)
    else:
        return []


def get_valid_addresses(ucs_host, extra_addresses):
    """Create a list of valid hostnames or IP addresses for this device"""
    valid_addresses = []
    invalid_addresses = []

    # Check if the UCS hostname is resolvable or IP address is valid
    try:
        socket.gethostbyname(ucs_host)
        valid_addresses.append(ucs_host)
    except socket.gaierror:
        invalid_addresses.append(ucs_host)

    # Check optional extra addresses to see if they are valid
    if extra_addresses:
        for addr in extra_addresses:
            try:
                socket.gethostbyname(addr)
                valid_addresses.append(addr)
            except socket.gaierror:
                invalid_addresses.append(addr)

    if not valid_addresses:
        print('All provided hostnames/addresses are invalid: {}'.format(
               [ucs_host] + extra_addresses))
        exit(1)
    return valid_addresses


def main():
    args = get_args()
    params = get_device_parameters(args)
    valid_addresses = get_valid_addresses(args.ucs_host,
                                          params['alternate_addresses'])

    login_success = False
    errors = []

    # Try all valid addresses until one succeeds or they all fail.
    for host_addr in valid_addresses:
        if params['server_type'] == 'ucsm':
            handle = UcsHandle(host_addr, params['username'],
                               params['password'])
            try:
                if not handle.login():
                    errors.append("Failed to connect to {} as user {}!".format(
                        args.ucs_host, params['username']))
                    continue
                else:
                    login_success = True
            except Exception as e:
                errors.append(str(e))
                continue

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
            break

        elif params['server_type'] == 'imc':
            handle = ImcHandle(host_addr, params['username'], params['password'])
            try:
                if not handle.login(timeout=10):
                    errors.append("Failed to connect to {} as user {}!".format(
                        args.ucs_host, params['username']))
                    continue
                else:
                    login_success = True
            except IndexError:
                errors.append(
                    'An exception was thrown trying to connect to {}. '
                    'It may be running an old/unsupported firmware version.'
                    ''.format(args.ucs_host))
                continue
            except Exception as e:
                errors.append(str(e))
                continue

            # Output the list of faults, if any, with the given severity level
            fault_list = handle.query_classid('faultInst')
            for fault in fault_list:
                if args.severity is None or args.severity == fault.severity:
                    print('{}: [{}] {}: {}'.format(fault.created, fault.severity,
                                                   fault.cause, fault.descr))
            handle.logout()
            break

        else:
            print("Unrecognized server type '{}'. "
                  "It should be 'ucsm' or 'imc'.".format(params['server_type']))
            exit(1)

    if not login_success:
        print('Failed all connection attempts:\n{}'.format('\n'.join(errors)))


main()

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
