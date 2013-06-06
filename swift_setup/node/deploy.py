""" See COPYING for license information """

import os
from sys import exit
from swift_setup.common.exceptions import ConfigFileError, \
    ResponseError, UploadTemplatesError, ConfigSyncError
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

        "Info for versioning section"
        self.conf = readconf(conf_file, 'versioning')
        self.ver_system = self.conf.get('versioning_system', 'git')
        self.repo_base = self.conf.get('repository_base', '/srv/git')
        self.repo_name = self.conf.get('repository_name',
                                       'swift-cluster-configs')

        "Info for swift section"
        self.conf = readconf(conf_file, 'swift_common')
        self.admin_ip = self.conf.get('admin_ip', '172.16.0.254')

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

    def _setup_swiftuser(self):
        """
        Setting up the user allows one to avoid issues when the UID
        could later on be changed from system setup to another due to
        some ubuntu changes as it has happened before with mlocate
        """
        if run('id swift', quiet=True).failed:
            sudo('groupadd -g 400 swift')
            sudo('useradd -u 400 -g swift -G adm -M -s /bin/false swift')

    def _pull_configs(self, sys_type):
        """
        This function will git clone the repo on the admin box
        and then sync it over to the root
        """
        if sudo('test -d /root/local').succeeded:
            sudo('mv -f /root/local /root/local.old')

        sudo('git clone git://%s/%s /root/local' % (self.admin_ip,
                                                    self.repo_name))
        if sudo('test -d /root/local/common').failed:
            status = 404
            msg = 'Directory was not found! (/root/local/common)'
            raise ConfigSyncError(status, msg)

        self._sync_files(sys_type)

    def _set_onhold(self, sys_type=''):
        """
        Sets the packages on hold to prevent upgrades
        """
        if sys_type == 'proxy':
            pkgs = self.swift_proxy.split() + self.swift_others.split()
        elif sys_type == 'storage':
            pkgs = self.swift_storage.split() + self.swift_others.split()
        elif sys_type == 'saio':
            pkgs = (self.swift_proxy.split() + self.swift_storage.split() +
                    self.swift_others.plit())
        else:
            pkgs = self.swift_generic.split()

        for name in pkgs:
            sudo('echo "%s hold" | dpkg --set-selections' % name)

    def _final_install_touches(self, sys_type=''):
        """
        Creates directories, sets ownerships, restart services .. etc
        """
        if sudo('test -e /var/cache/swift').failed:
            sudo('mkdir -p /var/cache/swift')
        sudo('chown -R swift.swift /var/cache/swift')

        if sudo('test -e /var/log/swift/stats').failed:
            sudo('mkdir -p /var/log/swift/stats')
        sudo('chown -R swift.swift /var/log/swift/stats')

        if sys_type == 'proxy':
            if sudo('test -e /var/log/swift/hourly').failed:
                sudo('mkdir -p /var/log/swift/hourly')

        sudo('chown -R swift.swift /etc/swift')
        sudo('rm -f /etc/swift/*.dpkg-dist')
        sudo('newaliases')

        if sys_type == 'storage' or sys_type == 'saio':
            if sudo('test -e /srv/node').failed:
                sudo('mkdir -p /srv/node')
            sudo('chown swift.swift /srv/node/*')

        """
        Restart/Start some processes
        """
        sudo('service procps restart')
        sudo('service ntp start')
        sudo('service exim4 restart')
        sudo('service syslog-ng restart')
        if sys_type == 'storage' or sys_type == 'saio':
            sudo('service rsync restart')

        """
        Bring up swift
        """
        if not sys_type == '':
            sudo('swift-init all restart')

    def _swift_install(self, sys_type='generic'):
        """
        Installs the swift packages according to the system type
        """
        sudo('''
             export DEBIAN_FRONTEND=noninteractive;
             apt-get update -qq -o Acquire::http::No-Cache=True;
             ''')
        self._setup_swiftuser()
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
                 apt-get install %s %s %s %s
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

    def _swift_proxy_setup(self):
        """
        Really just a wrapper function to identify task
        """
        with settings(hide('running', 'stdout', 'stderr', 'warnings')):
            self._pull_configs('proxy')
            self._swift_install('proxy')
            self._set_onhold('proxy')
            self._final_install_touches('proxy')

    def _swift_storage_setup(self):
        """
        Really just a wrapper function to identify task
        """
        with settings(hide('running', 'stdout', 'stderr', 'warnings')):
            self._pull_configs('storage')
            self._swift_install('storage')
            self._set_onhold('storage')
            self._final_install_touches('storage')

    def _swift_generic_setup(self):
        """
        Really just a wrapper function to identify task
        """
        with settings(hide('running', 'stdout', 'stderr', 'warnings')):
            self._pull_configs('generic')
            self._swift_install()
            self._set_onhold('generic')
            self._final_install_touches()

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
                    sudo('git clone -q file:///%s /root/local'
                         % (remote_path,))
                else:
                    sudo('git clone -q file:///%s /root/local'
                         % (remote_path,))

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
        elif type == 'proxy':
            execute(self._swift_proxy_setup, hosts=host_list)
        elif type == 'storage':
            execute(self._swift_storage_setup, hosts=host_list)
        elif type == 'generic':
            execute(self._swift_generic_setup, hosts=host_list)

        disconnect_all()
        return True
