..
      Copyright 2012 Nicolas Barcet for Canonical
                2013 New Dream Network, LLC (DreamHost)

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _installing_manually:

=====================
 Installing Manually
=====================


Storage Backend Installation
============================

This step is a prerequisite for the collector and API services. You may use
one of the listed database backends below to store Panko data.

MongoDB
-------

   Follow the instructions to install the MongoDB_ package for your operating
   system, then start the service. The required minimum version of MongoDB is
   2.4.x. You will also need to have pymongo_ 2.4 installed

   To use MongoDB as the storage backend, change the 'database' section in
   panko.conf as follows::

    [database]
    connection = mongodb://username:password@host:27017/panko

SQLalchemy-supported DBs
------------------------

   You may alternatively use any SQLAlchemy-supported DB such as
   `PostgreSQL` or `MySQL`.

   To use MySQL as the storage backend, change the 'database' section in
   panko.conf as follows::

    [database]
    connection = mysql+pymysql://username:password@host/panko?charset=utf8


.. _MongoDB: http://www.mongodb.org/
.. _pymongo: https://pypi.python.org/pypi/pymongo/


Installing the API Server
=========================

.. index::
   double: installing; API

.. note::

   The API server needs to be able to talk to keystone and panko's
   database. It is only required if you choose to store data in legacy
   database or if you inject new samples via REST API.

1. Clone the panko git repository to the server::

   $ cd /opt/stack
   $ git clone https://git.openstack.org/openstack/panko.git

2. As a user with ``root`` permissions or ``sudo`` privileges, run the
   panko installer::

   $ cd panko
   $ sudo python setup.py install

3. Create a service for panko in keystone::

     $ openstack service create event --name panko \
                                         --description "Panko Service"

4. Create an endpoint in keystone for panko::

     $ openstack endpoint create $PANKO_SERVICE \
                                 --region RegionOne \
                                 --publicurl "http://$SERVICE_HOST:8777" \
                                 --adminurl "http://$SERVICE_HOST:8777" \
                                 --internalurl "http://$SERVICE_HOST:8777"

   .. note::

     PANKO_SERVICE is the id of the service created by the first command
     and SERVICE_HOST is the host where the Panko API is running. The
     default port value for panko API is 8777. If the port value
     has been customized, adjust accordingly.

5. Choose and start the API server.

   Panko includes the ``panko-api`` command. This can be
   used to run the API server. For smaller or proof-of-concept
   installations this is a reasonable choice. For larger installations it
   is strongly recommended to install the API server in a WSGI host
   such as mod_wsgi (see :doc:`mod_wsgi`). Doing so will provide better
   performance and more options for making adjustments specific to the
   installation environment.

   If you are using the ``panko-api`` command it can be started
   as::

    $ panko-api

.. note::

   The development version of the API server logs to stderr, so you
   may want to run this step using a screen session or other tool for
   maintaining a long-running program in the background.
