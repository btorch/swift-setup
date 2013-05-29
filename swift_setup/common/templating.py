""" See COPYING for license information """

import sys
import os
from string import Template
from swift_setup.common.exceptions import ConfigFileError, \
    ResponseError, TemplateFileError
from swift_setup.common.utils import readconf


class TemplateGen(object):
    """
    This class is used for generation of the template files that
    will be used by fabric to push files to the servers that will
    be deploying

    :param conf_file: The configuration file location
    :param base_dir: Base location where config, templates, host files
                     are located for swift-setup
    """

    def __init__(self, conf_file, base_dir):
        self.conf = readconf(conf_file)
        self.base_dir = base_dir
        self.tmpl_dir = base_dir + '/templates'

        if not os.path.isdir(self.tmpl_dir):
            status = 404
            msg = 'Template directory not found [%s]' % self.tmpl_dir
            raise ResponseError(status, msg)

    def _update_files(self, templates):
        conf_vals = {}
        for v in self.conf.values():
            conf_vals.update(v)

        for template in templates.keys():
            subs = {}
            for val in templates[template]:
                subs[val] = conf_vals[val.lower()]

            try:
                fh = open(template, 'r')
                body = fh.read()
                fh.close()
            except Exception as e:
                status = 500
                msg = '%s (file: %s)' % (e.args[1], template)
                raise TemplateFileError(status, msg)

            s = Template(body)
            new_body = s.safe_substitute(subs)

            try:
                fh = open(template, 'w')
                fh.write(new_body)
                fh.close()
            except Exception as e:
                status = 500
                msg = '%s (file: %s)' % (e.args[1], template)
                raise TemplateFileError(status, msg)

    def _update_admin(self):
        location = self.tmpl_dir + '/admin/etc/'
        templates = {
            location + 'swift/dispersion.conf': ('KEYSTONE_AUTH_URI',
                                                 'KEYSTONE_ADMIN_TENANT',
                                                 'KEYSTONE_ADMIN_USER',
                                                 'KEYSTONE_ADMIN_KEY')
        }
        _update_files(templates)

    def _update_proxy(self):
        location = self.tmpl_dir + '/proxy/etc/'
        templates = {
            location + 'memcached.conf': ('MEMCACHE_MAXMEM',
                                          'SIM_CONNECTIONS'),
            location + 'swift/memcache.conf': ('MEMCACHE_SERVER_LIST', ),
            location + 'swift/proxy-server.conf': ('KEYSTONE_IP',
                                                   'KEYSTONE_PORT',
                                                   'KEYSTONE_AUTH_PROTO',
                                                   'KEYSTONE_AUTH_PORT',
                                                   'KEYSTONE_ADMIN_TENANT',
                                                   'KEYSTONE_ADMIN_USER',
                                                   'KEYSTONE_ADMIN_KEY',
                                                   'INFORMANT_IP'),
        }
        _update_files(templates)

    def _update_storage(self):
        usr_location = self.tmpl_dir + '/storage/usr/local/bin/'
        templates = {
            usr_location + 'drive_mount_check.py': ('OUTGOING_DOMAIN',
                                                    'EMAIL_ADDR')
        }
        self._update_files(templates)

    def _update_common(self):
        location = self.tmpl_dir + '/common/etc/'
        templates = {
            location + 'cron.d/swift_ring_check': ('ADMIN_IP', ),
            location + 'swift/swift.conf': ('SWIFT_HASH', ),
            location + 'syslog-ng/conf.d/swift-ng.conf': ('SYSLOG_IP', ),
            location + 'aliases': ('EMAIL_ADDR', 'PAGER_ADDR'),
            location + 'exim4/update-exim4.conf.conf': ('OUTGOING_DOMAIN',
                                                        'SMARTHOST',
                                                        'RELAY_NET')
        }
        _update_files(templates)

    def template_setup(self):
        """
        Used to modify the templates files that have placeholders
        with the information found in the config file
        """
        self._update_common()
        self._update_admin()
        self._update_proxy()
        self._update_storage()
        f = open(self.tmpl_dir + '/.initialized', 'w')
        f.close()
        return True
