import yaml
from qubes.qubes import QubesVmCollection
from qubes.qubes import QubesVmLabels
from qubes.qubes import QubesVmClasses

# Load VM Information
qvm_collection = QubesVmCollection()
qvm_collection.lock_db_for_writing()
qvm_collection.load()
qvm_collection.unlock_db()

qubes_vms = {}

vm_list = []

ansible_values = ['name',
                  'standalone',
                  'pool_name',
                  'memory',
                  'maxmem',
                  'mac',
                  'pci_strictreset',
                  'pci_e820_host',
                  'kernel',
                  'vcpus',
                  'kernelopts',
                  'drive',
                  'debug',
                  'default_user',
                  'include_in_backups',
                  'qrexec_installed',
                  'internal',
                  'guiagent_installed',
                  'seamless_gui_mode',
                  'autostart',
                  'qrexec_timeout',
                  'timezone']


for qube in qvm_collection.values():
    if qube.type.lower not in ('adminvm', 'templatevm'):
        current_qube = {}
        current_qube['state'] = 'present'
        current_qube['type'] = qube.type.lower()
        if qube.template is not None:
            current_qube['template'] = qube.template.name
        else:
            current_qube['template'] = 'none'
        current_qube['label'] = qube.label.name
        if qube.netvm is not None:
            current_qube['netvm'] = qube.netvm.name
        else:
            current_qube['netvm'] = 'none'
        if qube.dispvm_netvm is not None:
            current_qube['dispvm_netvm'] = qube.dispvm_netvm.name
        else:
            current_qube['dispvm_netvm'] = 'none'
        for value in ansible_values:
            try:
                current_qube[value] = getattr(qube, value)
            except:
                pass
        if not qube.is_template() and qube.template is None:
            current_qube['standalone'] = True
        else:
            current_qube['standalone'] = False
        vm_list.append(current_qube)

qubes_vms['qubes_vms'] = vm_list
print yaml.dump(qubes_vms, default_flow_style=False)
