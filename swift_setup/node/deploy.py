""" See COPYING for license information """

import os
from sys import exit
from swift_setup.common.exceptions import ConfigFileError, \
    ResponseError, UploadTemplatesError
from swift_setup.common.utils import readconf
from fabric.api import *
from fabric.network import *


class DeployNode(object):
    """
    This class is used for deploying the remote swift nodes

    :param conf_file: The configuration file location
    """

    def __init__(self, conf_file):
        self.base_dir = os.path.dirname(conf_file)

        "Info for common section"
        self.conf = readconf(conf_file, 'common')
        self.user = self.conf.get('ssh_user', 'swiftops')
        self.key = self.conf.get('ssh_key', '/home/swiftops/.ssh/id_rsa')
        self.apt_opts = self.conf.get('apt_options', '-y -qq --force-yes')
        self.swift_generic = self.conf.get('swift_generic')
        self.swift_proxy = self.conf.get('swift_proxy')
        self.swift_storage = self.conf.get('swift_storage')
        self.swift_others = self.conf.get('swift_others', '')

        "Info for versioning"
        self.conf = readconf(conf_file, 'versioning')
        self.ver_system = self.conf.get('versioning_system', 'git')
        self.repo_base = self.conf.get('repository_base', '/srv/git')
        self.repo_name = self.conf.get('repository_name',
                                       'swift-cluster-configs')

        "Some Fabric environmental variables"
        env.user = self.user
        env.key_filename = self.key
        env.warn_only = True
        env.parallel = True
        env.pool_size = 5

        "Keyring packages that might be needed"
        self.keyrings = ['ubuntu-cloud-keyring']

        "Utilities that will be install on all systems by the common setup"
        self.general_tools = ['python-software-properties', 'patch',
                              'debconf', 'bonnie++', 'dstat', 'ethtool',
                              'python-configobj', 'curl', 'subversion',
                              'git-core', 'iptraf', 'htop', 'syslog-ng',
                              'nmon', 'strace', 'iotop', 'debsums',
                              'python-pip', 'snmpd', 'snmp', 'bsd-mailx',
                              'xfsprogs', 'ntp', 'snmp-mibs-downloader',
                              'exim4', 'screen']

        if not os.path.isfile(self.key):
            status = 404
            msg = 'SSH private key could not be located [%s]' % self.key
            raise ResponseError(status, msg)

    def _sync_files(self, sys_type='generic'):
        """
        Syncing repo files to admin /
        """
        sys_path = {'admin': '/root/local/admin/',
                    'proxy': '/root/local/proxy/',
                    'storage': '/root/local/storage/',
                    'generic': '/root/local/common/'}

        if sys_type == 'generic':
            sudo('rsync -aq0c --exclude=".git" --exclude=".ignore" %s /'
                 % (sys_path[sys_type]))
        elif sys_type == 'saio':
            for x in ['generic', 'proxy', 'storage']:
                sudo('rsync -aq0c --exclude=".git" --exclude=".ignore" %s /'
                     % (sys_path[x]))
        else:
            sudo('rsync -aq0c --exclude=".git" --exclude=".ignore" %s /'
                 % (sys_path['generic']))
            sudo('rsync -aq0c --exclude=".git" --exclude=".ignore" %s /'
                 % (sys_path[sys_type]))

    def _swift_install(self, sys_type='generic'):
        """
        Installs the swift packages according to the system type
        """
        sudo('''
             export DEBIAN_FRONTEND=noninteractive;
             apt-get update -qq -o Acquire::http::No-Cache=True;
             ''')
        sudo('apt-get install %s %s' % (self.apt_opts, self.swift_generic))

        if sys_type == 'proxy':
            sudo('''
                 apt-get install %s %s %s
                 ''' % (self.apt_opts, self.swift_proxy, self.swift_others))
        elif sys_type == 'storage':
            sudo('''
                 apt-get install %s %s %s
                 ''' % (self.apt_opts, self.swift_storage, self.swift_others))
        elif sys_type == 'saio':
            sudo('''
                 apt-get install %s %s %s
                 ''' % (self.apt_opts, self.swift_proxy,
                        self.swift_storage, self.swift_others))

    def _common_setup(self):
        """
        Start by updating the apt db and performing an upgrade of general
        packages avaialable. Then install the cloud keyring and some
        other general tools that may come in handy at some point.
        """
        with settings(hide('running', 'stdout', 'stderr', 'warnings')):
            sudo('''
                 export DEBIAN_FRONTEND=noninteractive;
                 apt-get update -qq -o Acquire::http::No-Cache=True;
                 apt-get upgrade %s
                 ''' % self.apt_opts)
            sudo('''
                 export DEBIAN_FRONTEND=noninteractive;
                 apt-get install %s %s
                 ''' % (self.apt_opts,
                        ' '.join(self.keyrings + self.general_tools)))

    def _admin_setup(self):
        """
        This function will take care of setting up the admin
        system with what is needed
        """
        admin_pkgs = ['rsync', 'dsh', 'git', 'git-core', 'nginx',
                      'subversion', 'git-daemon-sysvinit']

        with settings(hide('running', 'stdout', 'stderr', 'warnings')):
            sudo('apt-get install %s %s ' % (self.apt_opts,
                                             ' '.join(admin_pkgs)))
            if sudo('test -e %s'
                    % (self.repo_base + '/' + self.repo_name)).failed:
                sudo('mkdir -p %s' % (self.repo_base + '/' + self.repo_name))
                local_path = self.tmpl_dir + '/*'
                remote_path = self.repo_base + '/' + self.repo_name + '/'
                if put(local_path, remote_path,
                       use_sudo=True, mirror_local_mode=True).failed:
                    status = 500
                    msg = '''
                          Uploading template files to remote admin system has
                          failed. [remote path: %s]
                          ''' % remote_path
                    disconnect_all()
                    raise UploadTemplatesError(status, msg)
                """
                Let's change the ownership of the pushed templates
                """
                sudo('chown -R root.root %s' % remote_path)

                """
                Initialize git repo
                """
                git_dir = remote_path + ".git"
                sudo('git --git-dir=%s --work-tree=%s init'
                     % (git_dir, remote_path))
                sudo('git --git-dir=%s --work-tree=%s add .'
                     % (git_dir, remote_path))
                sudo('git --git-dir=%s --work-tree=%s commit -qam "initial"'
                     % (git_dir, remote_path))
                if sudo('test -e %s' % git_dir).failed:
                    status = 500
                    msg = 'Issue initializing git repo on admin setup'
                    raise ResponseError(status, msg)

                if sudo('test -e /root/local').succeeded:
                    sudo('mv -f /root/local /root/local.old')
                    sudo('git clone -q file:///%s /root/local' % (remote_path,))
                else:
                    sudo('git clone -q file:///%s /root/local' % (remote_path,))

                """
                Syncing repo files to admin /
                """
                self._sync_files('admin')

                """
                Install swift packages for admin system
                """
                self._swift_install('admin')

                """
                Restarting some services
                """
                if sudo('service git-daemon start').failed:
                    status = 500
                    msg = 'Error restarting git-daemon'
                    raise ResponseError(status, msg)
                if sudo('service nginx restart').failed:
                    status = 500
                    msg = 'Error restarting nginx'
                    raise ResponseError(status, msg)
                """
                Reboot system
                """
                if sudo('reboot').failed:
                    status = 500
                    msg = 'Error trying to reboot system'
                    raise ResponseError(status, msg)
                else:
                    print "\nRebooting ... Please wait until it's back online"
                    print "to proceed with any other deploys\n"
                    print "Also verify that all required services"
                    print "are running on the admin system after the reboot"
            else:
                status = 500
                msg = 'System has been setup previously ... Aborting'
                raise ResponseError(status, msg)

    def deploy_me(self, type, platform, host_list):
        """
        This function is used to deploy the node type requested. It will
        use some helper function to accomplish this.
        """

        self.tmpl_dir = self.base_dir + '/templates'
        if not os.path.isfile(self.tmpl_dir + '/.initialized'):
            print "\tTemplates have not yet been initialized. Please first"
            print "\tmake proper changes to the swift-setup.conf file and than"
            print "\trun swift-setup init with sudo or as root user\n\n"
            return False

        execute(self._common_setup, hosts=host_list)

        if type == 'admin':
            execute(self._admin_setup, hosts=host_list)

        disconnect_all()
        return True
