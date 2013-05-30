""" See COPYING for license information """

import sys
import os
from swift_setup.common.exceptions import ConfigFileError
from ConfigParser import ConfigParser


def readconf(conf_file, section=None):
    """
    It will parse the config file according to what is
    needed.

    :param conf: The configuration file location
    :param section: A list of sections of the config to be parsed
    """
    c = ConfigParser()

    if not c.read(conf_file):
        status = 204
        msg = "No content found in the config file to be parsed"
        raise ConfigFileError(status, msg)

    if section:
        if c.has_section(section):
            conf = dict(c.items('common') + c.items(section))
    else:
        conf = {}
        for s in c.sections():
            conf.update({s: dict(c.items(s))})
    return conf

def generate_hosts_list(base_dir, host_group):
    '''
    Generates the list of hosts from a host group file and
    than feeds that list to the proper fabric roles.
    '''
    host_path = base_dir + '/hosts'
    host_file = host_path + '/' + host_group
    host_list = []
    try:
        if os.path.isfile(host_file):
            with open(host_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        if not line.startswith('#'):
                            host_list.append(line)
        else:
            status = 404
            msg = "Host group file not found (%s)" % dsh_file
            raise HostListError(status, msg)
    except:
        status = 404
        msg = "Problem reading host group file (%s)" % dsh_file
        raise HostListError(status, msg)

    if host_list:
        return host_list
    else:
        status = 204
        msg = "Host group file has no content (%s)" % dsh_file
        raise HostListError(status, msg)
