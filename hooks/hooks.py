#!/usr/bin/python

#
# Copyright 2012 Canonical Ltd.
#
# Authors:
#  James Page <james.page@ubuntu.com>
#

import shutil
import subprocess
import sys
import glob
import os

import utils


def install_www_scripts():
    for x in glob.glob('files/www/*'):
        shutil.copy(x, '/var/www/')


def install():
    utils.juju_log('INFO', 'Begin install hook.')
    utils.enable_pocket('multiverse')
    utils.configure_source()
    utils.install('radosgw',
                  'libapache2-mod-fastcgi',
                  'apache2')
    utils.juju_log('INFO', 'End install hook.')


def emit_cephconf():
    # Ensure ceph directory actually exists
    if not os.path.exists('/etc/ceph'):
        os.makedirs('/etc/ceph')

    cephcontext = {
        'mon_hosts': ' '.join(get_mon_hosts()),
        'hostname': utils.get_unit_hostname()
        }

    with open('/etc/ceph/ceph.conf', 'w') as cephconf:
        cephconf.write(utils.render_template('ceph.conf', cephcontext))


def emit_apacheconf():
    apachecontext = {
        "hostname": utils.unit_get('private-address')
        }
    with open('/etc/apache2/sites-available/rgw', 'w') as apacheconf:
        apacheconf.write(utils.render_template('rgw', apachecontext))


def apache_sites():
    utils.juju_log('INFO', 'Begin apache_sites.')
    subprocess.check_call(['a2dissite', 'default'])
    subprocess.check_call(['a2ensite', 'rgw'])
    utils.juju_log('INFO', 'End apache_sites.')


def apache_modules():
    utils.juju_log('INFO', 'Begin apache_sites.')
    subprocess.check_call(['a2enmod', 'fastcgi'])
    subprocess.check_call(['a2enmod', 'rewrite'])
    utils.juju_log('INFO', 'End apache_sites.')


def apache_reload():
    subprocess.call(['service', 'apache2', 'reload'])


def config_changed():
    utils.juju_log('INFO', 'Begin config-changed hook.')
    emit_cephconf()
    emit_apacheconf()
    install_www_scripts()
    apache_sites()
    apache_modules()
    apache_reload()
    utils.juju_log('INFO', 'End config-changed hook.')


def get_mon_hosts():
    hosts = []
    for relid in utils.relation_ids('mon'):
        for unit in utils.relation_list(relid):
            hosts.append(
                '{}:6789'.format(utils.get_host_ip(
                                    utils.relation_get('private-address',
                                                       unit, relid)))
                )

    hosts.sort()
    return hosts


def mon_relation():
    utils.juju_log('INFO', 'Begin mon-relation hook.')
    emit_cephconf()
    restart()
    utils.juju_log('INFO', 'End mon-relation hook.')


def gateway_relation():
    utils.juju_log('INFO', 'Begin gateway-relation hook.')
    utils.relation_set(hostname=utils.unit_get('private-address'),
                       port=80)
    utils.juju_log('INFO', 'Begin gateway-relation hook.')


def upgrade_charm():
    utils.juju_log('INFO', 'Begin upgrade-charm hook.')
    utils.juju_log('INFO', 'End upgrade-charm hook.')


def start():
    # In case we're being redeployed to the same machines, try
    # to make sure everything is running as soon as possible.
    subprocess.call(['service', 'radosgw', 'start'])
    utils.expose(port=80)


def restart():
    subprocess.call(['service', 'radosgw', 'restart'])


utils.do_hooks({
        'install': install,
        'config-changed': config_changed,
        'mon-relation-departed': mon_relation,
        'mon-relation-changed': mon_relation,
        'gateway-relation-joined': gateway_relation,
        'start': start,
        'upgrade-charm': config_changed,  # same function ATM
        })

sys.exit(0)
