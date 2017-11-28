# Install and start **Panko** service in devstack
#
# To enable Panko in devstack add an entry to local.conf that
# looks like
#
# [[local|localrc]]
# enable_plugin panko git://git.openstack.org/openstack/panko
#
# Several variables set in the localrc section adjust common behaviors
# of Panko (see within for additional settings):
#
#   PANKO_BACKEND:            Database backend (e.g. 'mysql', 'mongodb', 'es')

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

# Support potential entry-points console scripts in VENV or not
if [[ ${USE_VENV} = True ]]; then
    PROJECT_VENV["panko"]=${PANKO_DIR}.venv
    PANKO_BIN_DIR=${PROJECT_VENV["panko"]}/bin
else
    PANKO_BIN_DIR=$(get_python_exec_prefix)
fi


if [ -z "$PANKO_DEPLOY" ]; then
    # Default
    PANKO_DEPLOY=simple

    # Fallback to common wsgi devstack configuration
    if [ "$ENABLE_HTTPD_MOD_WSGI_SERVICES" == "True" ]; then
        PANKO_DEPLOY=mod_wsgi

    # Deprecated config
    elif [ -n "$PANKO_USE_MOD_WSGI" ] ; then
        echo_summary "PANKO_USE_MOD_WSGI is deprecated, use PANKO_DEPLOY instead"
        if [ "$PANKO_USE_MOD_WSGI" == True ]; then
            PANKO_DEPLOY=mod_wsgi
        fi
    fi
fi


function panko_service_url {
    echo "$PANKO_SERVICE_PROTOCOL://$PANKO_SERVICE_HOST:$PANKO_SERVICE_PORT"
}


# _panko_install_mongdb - Install mongodb and python lib.
function _panko_install_mongodb {
    # Server package is the same on all
    local packages=mongodb-server

    if is_fedora; then
        # mongodb client
        packages="${packages} mongodb"
    fi

    install_package ${packages}

    if is_fedora; then
        restart_service mongod
    else
        restart_service mongodb
    fi

    # give time for service to restart
    sleep 5
}

# Configure mod_wsgi
function _panko_config_apache_wsgi {
    sudo mkdir -p $PANKO_WSGI_DIR

    local panko_apache_conf=$(apache_site_config_for panko)
    local venv_path=""

    # Copy proxy vhost and wsgi file
    sudo cp $PANKO_DIR/panko/api/app.wsgi $PANKO_WSGI_DIR/app

    if [[ ${USE_VENV} = True ]]; then
        venv_path="python-path=${PROJECT_VENV["panko"]}/lib/$(python_version)/site-packages"
    fi

    sudo cp $PANKO_DIR/devstack/apache-panko.template $panko_apache_conf
    sudo sed -e "
        s|%PORT%|$PANKO_SERVICE_PORT|g;
        s|%APACHE_NAME%|$APACHE_NAME|g;
        s|%WSGIAPP%|$PANKO_WSGI_DIR/app|g;
        s|%USER%|$STACK_USER|g;
        s|%VIRTUALENV%|$venv_path|g
    " -i $panko_apache_conf
}

# Install required services for storage backends
function _panko_prepare_storage_backend {
    if [ "$PANKO_BACKEND" = 'mongodb' ] ; then
        pip_install_gr pymongo
        _panko_install_mongodb
    fi

    if [ "$PANKO_BACKEND" = 'es' ] ; then
        ${TOP_DIR}/pkg/elasticsearch.sh download
        ${TOP_DIR}/pkg/elasticsearch.sh install
    fi
}


# Create panko related accounts in Keystone
function _panko_create_accounts {
    if is_service_enabled panko-api; then

        create_service_user "panko" "admin"

        get_or_create_service "panko" "event" "OpenStack Telemetry Service"
        get_or_create_endpoint "event" \
            "$REGION_NAME" \
            "$(panko_service_url)" \
            "$(panko_service_url)" \
            "$(panko_service_url)"
    fi
}

# Activities to do before panko has been installed.
function preinstall_panko {
    echo_summary "Preinstall not in virtualenv context. Skipping."
}

# Remove WSGI files, disable and remove Apache vhost file
function _panko_cleanup_apache_wsgi {
    sudo rm -f "$PANKO_WSGI_DIR"/*
    sudo rmdir "$PANKO_WSGI_DIR"
    sudo rm -f $(apache_site_config_for panko)
}

function _panko_drop_database {
    if is_service_enabled panko-api ; then
        if [ "$PANKO_BACKEND" = 'mongodb' ] ; then
            mongo panko --eval "db.dropDatabase();"
        elif [ "$PANKO_BACKEND" = 'es' ] ; then
            curl -XDELETE "localhost:9200/events_*"
        fi
    fi
}

# cleanup_panko() - Remove residual data files, anything left over
# from previous runs that a clean run would need to clean up
function cleanup_panko {
    if [ "$PANKO_DEPLOY" == "mod_wsgi" ]; then
        _panko_cleanup_apache_wsgi
    fi
    _panko_drop_database
    sudo rm -f "$PANKO_CONF_DIR"/*
    sudo rmdir "$PANKO_CONF_DIR"
}

# Set configuration for storage backend.
function _panko_configure_storage_backend {
    if [ "$PANKO_BACKEND" = 'mysql' ] || [ "$PANKO_BACKEND" = 'postgresql' ] ; then
        iniset $PANKO_CONF database connection $(database_connection_url panko)
    elif [ "$PANKO_BACKEND" = 'es' ] ; then
        iniset $PANKO_CONF database connection es://localhost:9200
        ${TOP_DIR}/pkg/elasticsearch.sh start
    elif [ "$PANKO_BACKEND" = 'mongodb' ] ; then
        iniset $PANKO_CONF database connection mongodb://localhost:27017/panko
    else
        die $LINENO "Unable to configure unknown PANKO_BACKEND $PANKO_BACKEND"
    fi
    _panko_drop_database
}

# Configure Panko
function configure_panko {

    local conffile

    iniset $PANKO_CONF DEFAULT debug "$ENABLE_DEBUG_LOG_LEVEL"

    # Set up logging
    if [ "$SYSLOG" != "False" ]; then
        iniset $PANKO_CONF DEFAULT use_syslog "True"
    fi

    # Format logging
    if [ "$LOG_COLOR" == "True" ] && [ "$SYSLOG" == "False" ] && [ "$PANKO_DEPLOY" != "mod_wsgi" ]; then
        setup_colorized_logging $PANKO_CONF DEFAULT
    fi

    # Install the declarative configuration files to
    # the conf dir.
    # NOTE(cdent): Do not make this a glob as it will conflict
    # with rootwrap installation done elsewhere and also clobber
    # panko.conf settings that have already been made.
    # Anyway, explicit is better than implicit.
    cp $PANKO_DIR/etc/panko/api_paste.ini $PANKO_CONF_DIR

    configure_auth_token_middleware $PANKO_CONF panko $PANKO_AUTH_CACHE_DIR

    # Configure storage
    if is_service_enabled panko-api; then
        _panko_configure_storage_backend
    fi

    if is_service_enabled panko-api && [ "$PANKO_DEPLOY" == "mod_wsgi" ]; then
        _panko_config_apache_wsgi
    elif [ "$PANKO_DEPLOY" == "uwsgi" ]; then
        # iniset creates these files when it's called if they don't exist.
        PANKO_UWSGI_FILE=$PANKO_CONF_DIR/panko-uwsgi.ini

        rm -f "$PANKO_UWSGI_FILE"

        iniset "$PANKO_UWSGI_FILE" uwsgi http $PANKO_SERVICE_HOST:$PANKO_SERVICE_PORT
        iniset "$PANKO_UWSGI_FILE" uwsgi wsgi-file "$PANKO_DIR/panko/api/app.wsgi"
        # This is running standalone
        iniset "$PANKO_UWSGI_FILE" uwsgi master true
        # Set die-on-term & exit-on-reload so that uwsgi shuts down
        iniset "$PANKO_UWSGI_FILE" uwsgi die-on-term true
        iniset "$PANKO_UWSGI_FILE" uwsgi exit-on-reload true
        iniset "$PANKO_UWSGI_FILE" uwsgi threads 10
        iniset "$PANKO_UWSGI_FILE" uwsgi processes $API_WORKERS
        iniset "$PANKO_UWSGI_FILE" uwsgi enable-threads true
        iniset "$PANKO_UWSGI_FILE" uwsgi plugins python
        iniset "$PANKO_UWSGI_FILE" uwsgi lazy-apps true
        # uwsgi recommends this to prevent thundering herd on accept.
        iniset "$PANKO_UWSGI_FILE" uwsgi thunder-lock true
        # Override the default size for headers from the 4k default.
        iniset "$PANKO_UWSGI_FILE" uwsgi buffer-size 65535
        # Make sure the client doesn't try to re-use the connection.
        iniset "$PANKO_UWSGI_FILE" uwsgi add-header "Connection: close"
    fi
}

# init_panko() - Initialize etc.
function init_panko {
    # Get panko keystone settings in place
    _panko_create_accounts
    # Create cache dir
    sudo install -d -o $STACK_USER $PANKO_AUTH_CACHE_DIR
    rm -f $PANKO_AUTH_CACHE_DIR/*

    if is_service_enabled panko-api && is_service_enabled mysql postgresql ; then
        if [ "$PANKO_BACKEND" = 'mysql' ] || [ "$PANKO_BACKEND" = 'postgresql' ] || [ "$PANKO_BACKEND" = 'es' ] ; then
            recreate_database panko
            $PANKO_BIN_DIR/panko-dbsync
        fi
    fi
}

# Install Panko.
function install_panko {
    if is_service_enabled panko-api; then
        _panko_prepare_storage_backend
    fi

    setup_develop $PANKO_DIR
    sudo install -d -o $STACK_USER -m 755 $PANKO_CONF_DIR

    if [ "$PANKO_DEPLOY" == "mod_wsgi" ]; then
        install_apache_wsgi
    elif [ "$PANKO_DEPLOY" == "uwsgi" ]; then
        pip_install uwsgi
    fi
}

# start_panko() - Start running processes, including screen
function start_panko {
    if [[ "$PANKO_DEPLOY" == "mod_wsgi" ]]; then
        enable_apache_site panko
        restart_apache_server
        tail_log panko /var/log/$APACHE_NAME/panko.log
        tail_log panko-api /var/log/$APACHE_NAME/panko_access.log
    elif [ "$PANKO_DEPLOY" == "uwsgi" ]; then
        run_process panko-api "$PANKO_BIN_DIR/uwsgi $PANKO_UWSGI_FILE"
    else
        run_process panko-api "$PANKO_BIN_DIR/panko-api -d -v --config-file $PANKO_CONF"
    fi
}

# stop_panko() - Stop running processes
function stop_panko {
    if is_service_enabled panko-api ; then
        if [ "$PANKO_DEPLOY" == "mod_wsgi" ]; then
            disable_apache_site panko
            restart_apache_server
        else
            stop_process panko-api
        fi
    fi
}

# install_pankoclient() - Collect source and prepare
function install_pankoclient {
    if use_library_from_git "python-pankoclient"; then
        git_clone_by_name "python-pankoclient"
        setup_dev_lib "python-pankoclient"
    else
        pip_install pankoclient
    fi
}

# This is the main for plugin.sh
if is_service_enabled panko-api; then
    if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
        # Set up other services
        echo_summary "Configuring system services for Panko"
        preinstall_panko
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing Panko"
        # Use stack_install_service here to account for virtualenv
        stack_install_service panko
        install_pankoclient
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring Panko"
        configure_panko
    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        echo_summary "Initializing Panko"
        # Tidy base for panko
        init_panko
        # Start the services
        start_panko
    fi

    if [[ "$1" == "unstack" ]]; then
        echo_summary "Shutting Down Panko"
        stop_panko
    fi

    if [[ "$1" == "clean" ]]; then
        echo_summary "Cleaning Panko"
        cleanup_panko
    fi
fi

# Restore xtrace
$XTRACE
