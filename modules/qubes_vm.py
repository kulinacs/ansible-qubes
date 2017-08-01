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

def set_options(module):
    '''Parse options to pass to Qubes Admin API'''
    options = {}
    options['name'] = module.params['name']
    options['state'] = module.params['state']
    options['label'] = Qubes().get_label(module.params['label'])
    options['vm_class'] = Qubes().get_vm_class(module.params['vm_class'])
    options['template'] = Qubes().domains[module.params['template']]
    return options

def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(required=True, type='str'),
            state=dict(default='present', choices=['present', 'absent']),
            label=dict(type='str'),
            vm_class=dict(type='str'),
            template=dict(type='str')
        )
    )

    options = set_options(module)
    changed = False

    if options['state'] == 'present':
        if options['name'] not in Qubes().domains:
            changed = True
            Qubes().add_new_vm(options['vm_class'], options['name'],
                               options['label'], options['template'])
        else:
            changed = False
    elif options['state'] == 'absent':
        if options['name'] in Qubes().domains:
            changed = True
            del Qubes().domains[options['name']]
        else:
            changed = False


    if not QUBES_ADMIN:
        module.fail_json(msg='qubesadmin must be installed')

    module.exit_json(changed=changed)

if __name__ == '__main__':
        main()
