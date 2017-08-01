# Copyright (C) 2017  Nicklaus McClendon <nicklaus@kulinacs.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
ANSIBLE_METADATA = {'metadata_version': '1.0',
                                        'status': ['preview'],
                                        'supported_by': 'community'}

DOCUMENTATION = '''
---
module: qubes_vm
short_description: Manage individual qubes (Qubes virtual machines)
description:
    - Create, destroy, and configure qubes in Qubes
version_added: "2.4"
author: "Nicklaus McClendon (@kulinacs)
options:
  name:
    description:
      - Target qube
  state:
    description:
      - Desired state of target qube
    default: present
    choices: ['present', 'absent']
  label:
    description:
      - Desired label of target qube
  vm_class:
    description:
      - Desired vm_class of target qube (i.e. AppVM)
  template:
    description:
      - Desired template of target qube


requirements:
  - "python >= 3.5"
  - qubesadmin
'''
from ansible.module_utils.basic import AnsibleModule
import re
import os

try:
    from qubesadmin import Qubes
    QUBES_ADMIN = True
except ImportError:
    QUBES_ADMIN = False

def set_properties(options):
    '''Set Qube options'''
    changed = False
    qube = Qubes().domains[options['name']]
    for prop in qube.property_list():
        try:
            if options[prop] is not None and options[prop] != getattr(qube, prop):
                changed = True
                setattr(qube, prop, options[prop])
        except KeyError:
            pass
    return changed

def set_options(module):
    '''Parse options to pass to Qubes Admin API'''
    options = {}
    options['name'] = module.params['name']
    options['state'] = module.params['state']
    options['label'] = Qubes().get_label(module.params['label'])
    options['vm_class'] = Qubes().get_vm_class(module.params['vm_class'])
    options['template'] = Qubes().domains[module.params['template']]
    options['debug'] = module.params['debug']
    options['dispvm_allowed'] = module.params['dispvm_allowed']
    options['include_in_backups'] = module.params['include_in_backups']
    options['ip'] = module.params['ip']
    options['kernel'] = module.params['kernel']
    options['kernelopts'] = module.params['kernelopts']
    options['mac'] = module.params['mac']
    options['maxmem'] = module.params['maxmem']
    options['memory'] = module.params['memory']
    options['provides_network'] = module.params['provides_network']
    options['qrexec_timeout'] = module.params['qrexec_timeout']
    options['vcpus'] = module.params['vcpus']
    options['visible_gateway'] = module.params['visible_gateway']
    options['visible_ip'] = module.params['visible_ip']
    options['visible_netmask'] = module.params['visible_netmask']
    if module.params['default_dispvm'] is not None:
        options['default_dispvm'] = Qubes().domains[module.params['default_dispvm']]
    if module.params['netvm'] is not None:
        options['netvm'] = Qubes().domains[module.params['netvm']]
    return options

def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(required=True, type='str'),
            state=dict(default='present', choices=['present', 'absent']),
            label=dict(required=True, type='str'),
            vm_class=dict(required=True, type='str'),
            template=dict(required=True, type='str'),
            autostart=dict(type='bool'),
            debug=dict(type='bool'),
            dispvm_allowed=dict(type='bool'),
            include_in_backups=dict(type='bool'),
            ip=dict(type='str'),
            kernel=dict(type='str'),
            kernelopts=dict(type='str'),
            mac=dict(type='str'),
            maxmem=dict(type='int'),
            memory=dict(type='int'),
            provides_network=dict(type='bool'),
            qrexec_timeout=dict(type='int'),
            vcpus=dict(type='int'),
            visible_gateway=dict(type='str'),
            visible_ip=dict(type='str'),
            visible_netmask=dict(type='str'),
            default_dispvm=dict(type='str'),
            netvm=dict(type='str'),
        )
    )

    options = set_options(module)
    changed = False

    if options['state'] == 'present':
        if options['name'] not in Qubes().domains:
            changed = True
            Qubes().add_new_vm(options['vm_class'], options['name'],
                               options['label'], options['template'])
        changed = changed or set_properties(options)
    elif options['state'] == 'absent':
        if options['name'] in Qubes().domains:
            changed = True
            del Qubes().domains[options['name']]


    if not QUBES_ADMIN:
        module.fail_json(msg='qubesadmin must be installed')

    module.exit_json(changed=changed)

if __name__ == '__main__':
        main()
