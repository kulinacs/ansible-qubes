# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2017  Nicklaus McClendon <nicklaus@kulinacs.com>
# Copyright (C) 2010  Joanna Rutkowska <joanna@invisiblethingslab.com>
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
module: qubes
short_description: Manage individual qubes (Qubes virtual machines)
description:
    - Create, destroy, and configure qubes in Qubes
version_added: "2.3"
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
  type:
    description:
      - Desired type of target qube
    default: appvm
    choices: ['appvm', 'netvm', 'proxyvm', 'hvm', 'templatehvm']
  template:
    description:
      - Desired template of target qube
  standalone:
    description:
      - Bool, if the target qube should be standalone
  label:
    description:
      - The desired label for the target qube
    choices: ['red', 'orange', 'yellow', 'green', 'gray', 'blue', 'purple', 'black']
  pool:
    description:
      - The storage pool for the target qube
  memory:
    description:
      - The starting memory for the target qube
  maxmem:
    description:
      - The maximum memory for the target qube
  mac:
    description:
      - The mac address for the target qube (of the format XX:XX:XX:XX:XX:XX or auto)
  strictreset:
    description:
      - Bool, whether or not the VM can be assigned a device that doesn't support any reset method
  e820host:
    description:
      - Bool, whether or not the VM has a memory map of the host

requirements:
  - "python >= 2.6"
  - qubes
'''

from ansible.module_utils.basic import AnsibleModule
import re

try:
    from qubes.qubes import QubesVmCollection
    from qubes.qubes import QubesVmLabels
    from qubes.qubes import QubesVmClasses
    from qubes.qubes import QubesException
    from qubes.qubes import QubesHost
    QUBES_DOM0 = True
except ImportError:
    QUBES_DOM0 = False

vmtypes = {'appvm': 'QubesAppVm',
           'netvm': 'QubesNetVm',
           'proxyvm': 'QubesProxyVm',
           'hvm': 'QubesHVm',
           'templatehvm': 'QubesTemplateHVm'}


def verify_label(module, options):
    '''Verifies and sets the label'''
    if module.params['label'] is not None:
        options['args']['label'] = QubesVmLabels[module.params['label']]

    if module.params['label'] is None and options['state'] != 'absent':
        module.fail_json(msg='A label must be defined when creating a Qube')


def verify_template(module, qvm_collection, options):
    '''Verifies and sets the template'''
    if module.params['template'] is None:
        if options['type'] not in ('QubesHVm', 'QubesTemplateHVm'):
            options['args']['template'] = qvm_collection.get_default_template()
            if options['args']['template'] is None:
                module.fail_json(msg='No template specified and no default template found')
        else:
            options['args']['template'] = None
    else:
        options['args']['template'] = qvm_collection.get_vm_by_name(module.params['template'])
        if options['args']['template'] is None:
            module.fail_json(msg='TemplateVM not found: %s' % module.params['template'])
        elif not options['args']['template'].is_template():
            module.fail_json(msg='%s is not a TemplateVM' % module.params['template'])


def verify_standalone(options):
    '''Sets if standalone. Must be run after verify_template()'''
    if options['type'] == 'QubesHVm' and not options['args']['template']:
        options['standalone'] = True
    if options['type'] == 'QubesTemplateHVm':
        options['standalone'] = True


def verify_memory(module, options):
    '''Sets starting memory if passed, and verifies the value'''
    if module.params['memory'] is not None:
        if module.params['memory'] <= 0:
            module.fail_json(msg='Memory cannot be negative')
        qubes_host = QubesHost()
        if module.params['memory'] > qubes_host.memory_total/1024:
            module.fail_json(msg='This host has only %s MB of RAM' % str(qubes_host.memory_total/1024))
        options['args']['memory'] = module.params['memory']


def verify_maxmem(module, options):
    '''Sets max memory if passed, and verifies the value'''
    if module.params['maxmem'] is not None:
        if module.params['maxmem'] <= 0:
            module.fail_json(msg='Memory cannot be negative')
        qubes_host = QubesHost()
        if module.params['maxmem'] > qubes_host.memory_total/1024:
            module.fail_json(msg='This host has only %s MB of RAM' % str(qubes_host.memory_total/1024))
        options['args']['maxmem'] = module.params['maxmem']


def verify_mac(module, options):
    '''Sets mac address if passed, and verifies the value'''
    if module.params['mac'] is not None:
        if not re.match('[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}$|auto$', module.params['mac']):
            module.fail_json(msg='The MAC address must be auto or of the form XX:XX:XX:XX:XX:XX')
        if module.params['mac'] == 'auto':
            options['args']['mac'] = None
        else:
            options['args']['mac'] = module.params['mac']


def verify_options(module, qvm_collection):
    options = {}
    options['state'] = module.params['state']
    options['standalone'] = module.params['standalone']
    options['args'] = {}
    options['args']['name'] = module.params['name']
    options['args']['pool_name'] = module.params['pool']
    verify_label(module, options)
    options['type'] = vmtypes[module.params['type']]
    verify_template(module, qvm_collection, options)
    verify_standalone(options)
    options['base_template'] = options['args']['template']
    if options['standalone']:
        options['args']['template'] = None
    verify_memory(module, options)
    verify_maxmem(module, options)
    verify_mac(module, options)
    if module.params['strictreset'] is not None:
        options['args']['pci_strictreset'] = module.params['strictreset']
    if module.params['e820host'] is not None:
        options['args']['pci_e820_host'] = module.params['e820host']
    return options


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(required=True, type='str'),
            state=dict(default='present', choices=['present', 'absent']),
            type=dict(default='appvm', choices=['appvm', 'netvm', 'proxyvm', 'hvm', 'templatehvm']),
            template=dict(type='str'),
            standalone=dict(default=False, type='bool'),
            label=dict(choices=['red', 'orange', 'yellow', 'green', 'gray', 'blue', 'purple', 'black']),
            pool=dict(default='default', type='str'),
            memory=dict(type='int'),
            maxmem=dict(type='int'),
            mac=dict(type='str'),
            strictreset=dict(type='bool'),
            e820host=dict(default=False, type='bool'),
        )
    )

    if not QUBES_DOM0:
        module.fail_json(msg='This module must be run from QubeOS dom0')

    qvm_collection = QubesVmCollection()
    qvm_collection.lock_db_for_writing()
    qvm_collection.load()

    # Verify parameters
    changed = True
    options = verify_options(module, qvm_collection)

    if options['state'] == 'present':
        if qvm_collection.get_vm_by_name(options['args']['name']) is not None:
            changed = False
            qube = qvm_collection.get_vm_by_name(options['args']['name'])

            for key in options['args']:
                if key == 'pool_name':
                    if qube.pool_name != options['args']['pool_name']:
                        module.fail_json(msg='Existing VM storage pool cannot be changed')
                elif getattr(qube, key) != options['args'][key]:
                    setattr(qube, key, options['args'][key])
                    changed = True

            if not isinstance(qube, QubesVmClasses[options['type']]):
                module.fail_json(msg='Existing VM type cannot be changed')

        else:
            try:
                qube = qvm_collection.add_new_vm(options['type'], **options['args'])
            except QubesException as e:
                module.fail_json(msg='Unable to create VM: %s' % e)

            qube.create_on_disk(source_template=options['base_template'])

    elif options['state'] == 'absent':
        if qvm_collection.get_vm_by_name(options['args']['name']) is None:
            changed = False
        else:
            qube = qvm_collection.get_vm_by_name(options['args']['name'])

            if qube.is_running():
                try:
                    qube.force_shutdown()
                except (IOError, OSError, QubesException) as e:
                    module.fail_json(msg='Unable to shutdown VM: %s' % e)

            if qube.is_template(): # Report what VMs use this template
                dependent_qubes = qube.qvm_collection.get_vms_based_on(qube.qid)
                if len(dependent_qubes) > 0:
                    module.fail_json(msg='Please remove VMs dependent on this template first')
                if qvm_collection.default_template_qid == qube.qid:
                    qvm_collection.default_template_qid = None

            if qube.is_netvm():
                if qvm_collection.default_netvm_qid == qube.qid:
                    qvm_collection.default_netvm_qid = None

            if qube.installed_by_rpm:
                module.fail_json(msg='Qube managed by RPM/DNF')

            qube.remove_from_disk()
            qvm_collection.pop(qube.qid)

    qvm_collection.save()
    qvm_collection.unlock_db()
    module.exit_json(changed=changed)

if __name__ == '__main__':
        main()
