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
