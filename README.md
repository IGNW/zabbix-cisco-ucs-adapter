# Cisco UCS adapter for Zabbix

This repo contains a script that can be plugged into a 
[Zabbix](https://www.zabbix.com/]) monitoring system to allow it to pull a list
of current faults from a UCS Manager, optionally filtered by severity.

## Dependencies
* Python 3
* [ucsmsdk](https://github.com/CiscoUcs/ucsmsdk) Python module

## Installation (Unix-based)
1. Make the *ucs_fault_query.py* file executable
    * `chmod +x ucs_fault_query.py`
2. Move it to the Zabbix external scripts directory
    * `mv ucs_fault_query.py /usr/lib/zabbix/externalscripts/`
3. Edit the *ucsm_credentials.ini* file and input valid credentials.
    * Note: A read-only account is recommended.
4. Move the *ucsm_credentials.ini* file to /etc
    * `mv ucsm_credentials.ini /etc`
    * Note: An alternate location/filename can be specified when running the
    script by using the *--config* option
5. Run the script from the CLI to verify functionality.

## CLI usage and example
```
usage: ucs_fault_query.py [-h] [--config CONFIG] [--severity SEVERITY] ucs_host

Get a list of current UCS device faults.

positional arguments:
  ucs_host             IP address or hostname of the UCS device.

optional arguments:
  -h, --help           show this help message and exit
  --config CONFIG      (Optional) Location of configuration file containing
                       UCS credentials. (Default: /etc/ucsm_credentials.ini)
  --severity SEVERITY  (Optional) Severity level to use as a filter.
                       ['critical', 'major', 'minor', 'warning', 'info']

$ ./ucs_fault_query.py --severity warning 10.2.1.237
2018-01-10T20:46:31.755: [warning] link-missing: Connection to Adapter 1 eth interface 1 in server 1 missing
2018-01-10T20:46:31.756: [warning] link-missing: Connection to Management Port 1 in server 1 is missing
...

$ ./ucs_fault_query.py --severity critical 10.2.1.237
$
# Note: No output was generated above because there were no Critical faults.
```
If no severity is provided, then all faults will be returned.

## Zabbix Configuration

Pictured below is an example of how you could configure an item in Zabbix to 
poll this data by running the script as an External check. The host interface 
is only useful to have a reference to the IP address. No Zabbix agent is
needed for this script to function.

![Zabbix item configuration](docs/item_config.png)

Next you would create a trigger to alert you when the item returns a non-empty
result.

![Zabbix trigger configuration](docs/trigger_expression.png)

Repeat the above steps to create additional items/triggers for additional 
severities (critical, major, etc.) as needed. Now you will be able to see 
alerts when any of the monitored UCS faults are detected, and then look at the
item history to see more details.

![Zabbix trigger alert example](docs/trigger_alert.png)

![History context menu](docs/trigger_history_drilldown.png)

![Fault history details](docs/fault_report_text.png)
