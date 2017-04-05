==========================
Enabling Panko in DevStack
==========================

1. Download Devstack::

    git clone https://git.openstack.org/openstack-dev/devstack
    cd devstack

2. Add this repo as an external repository in ``local.conf`` file::

    [[local|localrc]]
    enable_plugin panko https://git.openstack.org/openstack/panko

   To use stable branches, make sure devstack is on that branch, and specify
   the branch name to enable_plugin, for example::

    enable_plugin panko https://git.openstack.org/openstack/panko stable/newton

   There are some options, such as PANKO_BACKEND, defined in
   ``panko/devstack/settings``, they can be used to configure the
   installation of Panko. If you don't want to use their default value,
   you can set a new one in ``local.conf``.

3. Run ``stack.sh``.
