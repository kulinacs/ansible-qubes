Ansible Qubes
=============

*HIGHLY EXPERIMENTAL* Some modules are designed to be run in dom0, which has full access to your system. VM Management implementation closely follows that of `qubes-core-admin`, however, this repo is widely untested.

Ansible modules designed for Qubes management with minimal dependencies. (Ideally only Ansible and Qubes libraries)

Current Functionality
---------------------

### Qubes Module

Configures state of individual Qubes (VMs) on the system. NOTE: Setting a VM as absent will delete the VM even if it is running

### dump_vms.py

Dumps current vm properties into a yaml file that can be consumed by Ansible. Currently needs work to support correctly setting auto settings.
