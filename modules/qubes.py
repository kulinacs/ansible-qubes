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
  pool_name:
    description:
      - The storage pool_name for the target qube
  memory:
    description:
      - The starting memory for the target qube
  maxmem:
    description:
      - The maximum memory for the target qube
  mac:
    description:
      - The mac address for the target qube (of the format XX:XX:XX:XX:XX:XX or auto)
  pci_strictreset:
    description:
      - Bool, whether or not the VM can be assigned a device that doesn't support any reset method
  pci_e820_host:
    description:
      - Bool, whether or not the VM has a memory map of the host
  netvm:
    description:
      - The netvm for the target qube. Can be default, none, or a vm name.
  dispvm_netvm:
    description:
      - The netvm for disposable vms based on the target qube. Can be default, none, or a vm name.
  kernel:
    description:
      - The kernel for the target qube. Can be default, none, or a kernel name 
  vcpus:
    description:
      - The number of vcpus for the target qube
  kernelopts:
    description:
      - The kernelopt for the target qube. Can be default or a string of options 
  drive:
    description:
      - The drive for the target qube. Can be none or the drive
  debug:
    description:
      - Bool
  default_user:
    description:
      - The default user for the target qube
  include_in_backups:
    description:
      - Bool
  internal:
    description:
      - Bool
  guiagent_installed:
    description:
      - Bool
  seemless_gui_mode:
    description:
      - Bool
  autostart:
    description:
      - Bool
  qrexec_timeout:
    description:
      - qrexec_timeout for the target qube
  timezone:
    description:
      - timezone for the target qube

requirements:
  - "python >= 2.6"
  - qubes
'''

from ansible.module_utils.basic import AnsibleModule
import re
import os

try:
    from qubes.qubes import QubesVmCollection
    from qubes.qubes import QubesVmLabels
    from qubes.qubes import QubesVmClasses
    from qubes.qubes import QubesException
    from qubes.qubes import QubesHost
    from qubes.qubes import system_path
    QUBES_DOM0 = True
except ImportError:
    QUBES_DOM0 = False

vmtypes = {'appvm': 'QubesAppVm',
           'netvm': 'QubesNetVm',
           'proxyvm': 'QubesProxyVm',
           'hvm': 'QubesHVm',
           'templatehvm': 'QubesTemplateHVm'}


def set_label(module, options):
    '''Verifies and sets the label'''
    if module.params['label'] is not None:
        options['args']['label'] = QubesVmLabels[module.params['label']]

    if module.params['label'] is None and options['state'] != 'absent':
        module.fail_json(msg='A label must be defined when creating a Qube')


def set_template(module, qvm_collection, options):
    '''Verifies and sets the template'''
    if module.params['template'] is None or module.params['template'] == 'none':
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


def set_standalone(options):
    '''Sets if standalone. Must be run after set_template()'''
    if options['type'] == 'QubesHVm' and not options['args']['template']:
        options['standalone'] = True
    if options['type'] == 'QubesTemplateHVm':
        options['standalone'] = True


def set_memory(module, options):
    '''Sets starting memory if passed, and verifies the value'''
    if module.params['memory'] is not None:
        if module.params['memory'] <= 0:
            module.fail_json(msg='Memory cannot be negative')
        qubes_host = QubesHost()
        if module.params['memory'] > qubes_host.memory_total/1024:
            module.fail_json(msg='This host has only %s MB of RAM' % str(qubes_host.memory_total/1024))
        options['args']['memory'] = module.params['memory']


def set_maxmem(module, options):
    '''Sets max memory if passed, and verifies the value'''
    if module.params['maxmem'] is not None:
        if module.params['maxmem'] <= 0:
            module.fail_json(msg='Memory cannot be negative')
        qubes_host = QubesHost()
        if module.params['maxmem'] > qubes_host.memory_total/1024:
            module.fail_json(msg='This host has only %s MB of RAM' % str(qubes_host.memory_total/1024))
        options['args']['maxmem'] = module.params['maxmem']


def set_mac(module, options):
    '''Sets mac address if passed, and verifies the value'''
    if module.params['mac'] is not None:
        if not re.match('[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}$|auto$', module.params['mac']):
            module.fail_json(msg='The MAC address must be auto or of the form XX:XX:XX:XX:XX:XX')
        if module.params['mac'] == 'auto':
            options['args']['mac'] = None
        else:
            options['args']['mac'] = module.params['mac']


def set_netvm(module, qvm_collection, options):
    '''Sets netvm if passed, and verifies the value'''
    if module.params['netvm'] is not None:
        if module.params['netvm'] == 'none':
            options['args']['netvm'] = None
            options['args']['uses_default_netvm'] = False
        elif module.params['netvm'] == 'default':
            options['args']['netvm'] = qvm_collection.get_default_netvm()
            options['args']['uses_default_netvm'] = True
        else:
            options['args']['netvm'] = qvm_collection.get_vm_by_name(module.params['netvm'])
            if options['args']['netvm'] is None:
                module.fail_json(msg='netvm: %s does not exist' % module.params['netvm'])
            if not options['args']['netvm'].is_netvm():
                module.fail_json(msg='%s is not a netvm' % module.params['netvm'])
            options['args']['uses_default_netvm'] = False


def set_dispvm_netvm(module, qvm_collection, options):
    '''Sets dispvm_netvm if passed, and verifies the value'''
    if module.params['dispvm_netvm'] is not None:
        if module.params['dispvm_netvm'] == 'none':
            options['args']['dispvm_netvm'] = None
            options['args']['uses_default_dispvm_netvm'] = False
        elif module.params['dispvm_netvm'] == 'default':
            options['args']['uses_default_dispvm_netvm'] = True
        else:
            options['args']['dispvm_netvm'] = qvm_collection.get_vm_by_name(module.params['dispvm_netvm'])
            if options['args']['dispvm_netvm'] is None:
                module.fail_json(msg='dispvm_netvm: %s does not exist' % module.params['dispvm_netvm'])
            if not options['args']['dispvm_netvm'].is_netvm():
                module.fail_json(msg='%s is not a dispvm_netvm' % module.params['dispvm_netvm'])
            options['args']['uses_default_dispvm_netvm'] = False


def set_kernel(module, qvm_collection, options):
    '''Sets kernel if passed, and verifies the value'''
    if module.params['kernel'] is not None:
        if module.params['kernel'] == 'none':
            options['args']['kernel'] = None
            options['args']['uses_default_kernel'] = False
        elif module.params['kernel'] == 'default':
            options['args']['kernel'] = qvm_collection.get_default_kernel()
            options['args']['uses_default_kernel'] = True
        else:
            if not os.path.exists(os.path.join(system_path["qubes_kernels_base_dir"], module.params['kernel'])):
                module.fail_json(msg='kernel: %s does not exist' % module.params['kernel'])
            options['args']['kernel'] = module.params['kernel']
            options['args']['uses_default_kernel'] = False


def set_vcpus(module, options):
    '''Sets starting vcpus if passed, and verifies the value'''
    if module.params['vcpus'] is not None:
        if module.params['vcpus'] <= 0:
            module.fail_json(msg='Vcpus cannot be negative')
        qubes_host = QubesHost()
        if module.params['vcpus'] > qubes_host.no_cpus:
            module.fail_json(msg='This host has only %s cpus' % str(qubes_host.no_cpus))
        options['args']['vcpus'] = module.params['vcpus']


def set_kernelopts(module, options):
    '''Sets kernelopts if passed, and verifies the value'''
    if module.params['kernelopts'] is not None:
        if module.params['kernelopts'] == 'default':
            options['args']['uses_default_kernelopts'] = True
        else:
            options['args']['kernelopts'] = module.params['kernelopts']
            options['args']['uses_default_kernelopts'] = False


def set_drive(module, options):
    '''Sets drive if passed, and verifies the value'''
    if module.params['drive'] is not None:
        if module.params['drive'] == 'none':
            options['args']['drive'] = None
        else:
            options['args']['drive'] = module.params['drive']


def set_qrexec_timeout(module, options):
    '''Sets qrexec_timeout if passed, and verifies the value'''
    if module.params['qrexec_timeout'] is not None:
        if module.params['qrexec_timeout'] < 0:
            module.fail_json(msg='qrexec_timeout cannot be negative')
        options['args']['qrexec_timeout'] = module.params['qrexec_timeout']


def set_timezone(module, options):
    '''Sets timezone  if passed, and verifies the value'''
    if module.params['timezone'] is not None:
        if module.params['timezone'] == 'localtime':
            options['args']['timezone'] = module.params['timezone']
        else:
            try:
                options['args']['timezone'] = int(module.params['timezone'])
            except:
                module.fail_json(msg='timezone must be localtime or an integer offset')


def set_options(module, qvm_collection):
    options = {}
    options['state'] = module.params['state']
    options['standalone'] = module.params['standalone']
    options['args'] = {}
    options['args']['name'] = module.params['name']
    options['args']['pool_name'] = module.params['pool_name']
    set_label(module, options)
    options['type'] = vmtypes[module.params['type']]
    set_template(module, qvm_collection, options)
    set_standalone(options)
    options['base_template'] = options['args']['template']
    if options['standalone']:
        options['args']['template'] = None
    set_memory(module, options)
    set_maxmem(module, options)
    set_mac(module, options)
    if module.params['pci_strictreset'] is not None:
        options['args']['pci_strictreset'] = module.params['pci_strictreset']
    if module.params['pci_e820_host'] is not None:
        options['args']['pci_e820_host'] = module.params['pci_e820_host']
    set_netvm(module, qvm_collection, options)
    set_dispvm_netvm(module, qvm_collection, options)
    set_kernel(module, qvm_collection, options)
    set_vcpus(module, options)
    set_kernelopts(module, options)
    set_drive(module, options)
    if module.params['debug'] is not None:
        options['args']['debug'] = module.params['debug']
    if module.params['default_user'] is not None:
        options['args']['default_user'] = module.params['default_user']
    if module.params['include_in_backups'] is not None:
        options['args']['include_in_backups'] = module.params['include_in_backups']
    if module.params['qrexec_installed'] is not None:
        options['args']['qrexec_installed'] = module.params['qrexec_installed']
    if module.params['internal'] is not None:
        options['args']['internal'] = module.params['internal']
    if module.params['guiagent_installed'] is not None:
        options['args']['guiagent_installed'] = module.params['guiagent_installed']
    if module.params['seamless_gui_mode'] is not None:
        options['args']['seamless_gui_mode'] = module.params['seamless_gui_mode']
    if module.params['autostart'] is not None:
        options['args']['autostart'] = module.params['autostart']
    set_qrexec_timeout(module, options)
    set_timezone(module, options)
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
            pool_name=dict(default='default', type='str'),
            memory=dict(type='int'),
            maxmem=dict(type='int'),
            mac=dict(type='str'),
            pci_strictreset=dict(type='bool'),
            pci_e820_host=dict(default=False, type='bool'),
            netvm=dict(type='str'),
            dispvm_netvm=dict(type='str'),
            kernel=dict(type='str'),
            vcpus=dict(type='int'),
            kernelopts=dict(type='str'),
            drive=dict(type='str'),
            debug=dict(type='bool'),
            default_user=dict(type='str'),
            include_in_backups=dict(type='bool'),
            qrexec_installed=dict(type='bool'),
            internal=dict(type='bool'),
            guiagent_installed=dict(type='bool'),
            seamless_gui_mode=dict(type='bool'),
            autostart=dict(type='bool'),
            qrexec_timeout=dict(type='int'),
            timezone=dict(),
        )
    )

    if not QUBES_DOM0:
        module.fail_json(msg='This module must be run from QubeOS dom0')

    qvm_collection = QubesVmCollection()
    qvm_collection.lock_db_for_writing()
    qvm_collection.load()

    # Set parameters
    changed = True
    options = set_options(module, qvm_collection)

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
