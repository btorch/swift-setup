""" See COPYING for license information """

import os
from swift_setup.common.exceptions import ConfigFileError, ResponseError
from swift_setup.common.utils import readconf
from fabric.api import *
from fabric.network import *


class DeployNode(object):
    """
    This class is used for deploying the remote swift nodes

    :param conf_file: The configuration file location
    """

    def __init__(self, conf_file):
        self.conf = readconf(conf_file, 'common')
        self.user = self.conf['ssh_user']
        self.key = self.conf['ssh_key']
        self.apt_opts = self.conf['apt_options']
        self.swift_generic = self.conf['swift_generic']
        self.swift_proxy = self.conf['swift_proxy']
        self.swift_storage = self.conf['swift_storage']

        if 'swift_others' in self.conf:
            self.swift_others = self.conf['swift_others']
        else:
            self.swift_others = None

        "Some Fabric environmental variables"
        env.user = self.user
        env.key_filename = self.key
        env.warn_only = True
        env.parallel = True
        env.pool_size = 5

        "Keyring packages that might be needed"
        keyrings = ['ubuntu-cloud-keyring']

        "Utilities that will be install on all systems by the common setup"
        self.general_tools = ['python-software-properties', 'patch',
                              'debconf', 'bonnie++', 'dstat', 'ethtool',
                              'python-configobj', 'curl', 'subversion',
                              'git-core', 'iptraf', 'htop', 'syslog-ng',
                              'nmon', 'strace', 'iotop', 'debsums',
                              'python-pip', 'snmpd', 'snmp', 'bsd-mailx',
                              'xfsprogs', 'ntp', 'snmp-mibs-downloader',
                              'exim4']

        if not os.path.isfile(self.key):
            status = 404
            msg = 'SSH private key could not be located [%s]' % self.key
            raise ResponseError(status, msg)

    def _common(self):
        """
        Start by updating the apt db and performing an upgrade of general
        packages avaialable. Then install the cloud keyring and some
        other general tools that may come in handy at some point.
        """
        sudo('apt-get update -qq -o Acquire::http::No-Cache=True ')
        sudo('export DEBIAN_FRONTEND=noninteractive; apt-get upgrade %s '
             % self.apt_opts)
        sudo('apt-get install %s %s' % (self.apt_opts,
                                        ' '.join(self.keyrings)))
        sudo('''
             export DEBIAN_FRONTEND=noninteractive;
             apt-get install %s %s
             ''' % (self.apt_opts, ' '.join(self.general_tools)))

    def deploy_me(self, type, platform, host_list):
        """
        This function is used to deploy the node type requested. It will
        use some helper function to accomplish this.
        """
        with settings(hide('running', 'stdout', 'stderr')):
            execute(self._common, hosts=host_list)

        disconnect_all()
        return True
