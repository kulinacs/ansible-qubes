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
    choices: ['yes', 'no']
  label:
    description:
      - The desired label for the target qube
    choices: ['red', 'orange', 'yellow', 'green', 'gray', 'blue', 'purple', 'black']
  pool:
    description:
      - The storage pool for the target qube

requirements:
  - "python >= 2.6"
  - qubes
'''

from ansible.module_utils.basic import AnsibleModule

try:
    from qubes.qubes import QubesVmCollection
    from qubes.qubes import QubesVmLabels
    from qubes.qubes import QubesException
    QUBES_DOM0 = True
except ImportError:
    QUBES_DOM0 = False


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
        )
    )

    if not QUBES_DOM0:
        module.fail_json(msg='This module must be run from QubeOS dom0')

    qvm_collection = QubesVmCollection()
    qvm_collection.lock_db_for_writing()
    qvm_collection.load()

    changed = True
    name = module.params['name']
    state = module.params['state']
    pool = module.params['pool']
    standalone = module.params['standalone']

    if module.params['label'] is not None:
        label = QubesVmLabels[module.params['label']]

    vmtypes = {'appvm': 'QubesAppVm',
               'netvm': 'QubesNetVm',
               'proxyvm': 'QubesProxyVm',
               'hvm': 'QubesHVm',
               'templatehvm': 'QubesTemplateHVm'}
    vmtype = vmtypes[module.params['type']]

    if module.params['template'] is None:
        if vmtype not in ('QubesHVm', 'QubesTemplateHVm'):
            template = qvm_collection.get_default_template()
            if template is None:
                module.fail_json(msg='No template specified and no default template found')
    else:
        template = qvm_collection.get_vm_by_name(module.params['template'])
        if template is None:
            module.fail_json(msg='TemplateVM not found: %s' % module.params['template'])
        elif not template.is_template():
            module.fail_json(msg='%s is not a TemplateVM' % module.params['template'])

    if vmtype == 'QubesHVm' and not template:
        standalone = True

    if vmtype == 'QubesTemplateHVm':
        standalone = True

    if standalone:
        new_vm_template = None
    else:
        new_vm_template = template

    if state == 'present':
        if qvm_collection.get_vm_by_name(name) is not None:
            changed = False
        else:
            try:
                qube = qvm_collection.add_new_vm(vmtype, name=name,
                                                 template=new_vm_template,
                                                 label=label, pool_name=pool)
            except QubesException as e:
                module.fail_json(msg='Unable to create VM: %s' % e)

            qube.create_on_disk(source_template=template)

    elif state == 'absent':
        if qvm_collection.get_vm_by_name(name) is None:
            changed = False
        else:
            qube = qvm_collection.get_vm_by_name(name)

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
