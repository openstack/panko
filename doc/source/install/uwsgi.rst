==============================
 Installing the API with uwsgi
==============================

Panko comes with a few example files for configuring the API
service to run behind Apache with ``mod_wsgi``.

app.wsgi
========

The file ``panko/api/app.wsgi`` sets up the V2 API WSGI
application. The file is installed with the rest of the Panko
application code, and should not need to be modified.

Example of uwsgi configuration file
===================================


Create panko-uwsgi.ini file::

    [uwsgi]
    http = 0.0.0.0:8041
    wsgi-file = <path_to_panko>/panko/api/app.wsgi
    plugins = python
    # This is running standalone
    master = true
    # Set die-on-term & exit-on-reload so that uwsgi shuts down
    exit-on-reload = true
    die-on-term = true
    # uwsgi recommends this to prevent thundering herd on accept.
    thunder-lock = true
    # Override the default size for headers from the 4k default. (mainly for keystone token)
    buffer-size = 65535
    enable-threads = true
    # Set the number of threads usually with the returns of command nproc
    threads = 8
    # Make sure the client doesn't try to re-use the connection.
    add-header = Connection: close
    # Set uid and gip to an appropriate user on your server. In many
    # installations ``panko`` will be correct.
    uid = panko
    gid = panko

Then start the uwsgi server::

    uwsgi ./panko-uwsgi.ini

Or start in background with::

    uwsgi -d ./panko-uwsgi.ini

Configuring with uwsgi-plugin-python on Debian/Ubuntu
=====================================================

Install the Python plugin for uwsgi::

    apt-get install uwsgi-plugin-python

Run the server::

    uwsgi_python --master --die-on-term --logto /var/log/panko/panko-api.log \
        --http-socket :8042 --wsgi-file /usr/share/panko-common/app.wsgi
