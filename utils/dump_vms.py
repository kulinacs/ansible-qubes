import yaml
from qubesadmin import Qubes
from qubesadmin.vm import AppVM

qubes_vms = {}

vm_list = []

ansible_values = [ 'autostart',
                   'backup_timestamp',
                   'debug',
                   'default_user',
                   'dispvm_allowed',
                   'gateway',
                   'include_in_backups',
                   'installed_by_rpm',
                   'ip',
                   'kernel',
                   'label',
                   'mac',
                   'maxmem',
                   'memory',
                   'name',
                   'provides_network',
                   'qid',
                   'qrexec_timeout',
                   'stubdom_mem',
                   'stubdom_xid',
                   'updateable',
                   'uuid',
                   'vcpus',
                   'virt_mode',
                   'visible_gateway',
                   'visible_ip',
                   'visible_netmask',
                   'xid',
                   'default_dispvm',
                   'kernelopts',
                   'netvm',
                   'template']

for qube in Qubes().domains:
    if isinstance(qube, AppVM):
        current_qube = {}
        current_qube['state'] = 'present'
        print(getattr(qube, 'name'))
        for value in ansible_values:
            try:
                current_qube[value] = getattr(qube, value)
            except:
                pass
        vm_list.append(current_qube)

qubes_vms['qubes_vms'] = vm_list
print(yaml.dump(qubes_vms, default_flow_style=False))
