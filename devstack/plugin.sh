# Install and start **Ceilometer** service in devstack
#
# To enable Ceilometer in devstack add an entry to local.conf that
# looks like
#
# [[local|localrc]]
# enable_plugin ceilometer git://git.openstack.org/openstack/ceilometer
#
# Several variables set in the localrc section adjust common behaviors
# of Ceilometer (see within for additional settings):
#
#   CEILOMETER_BACKEND:            Database backend (e.g. 'mysql', 'mongodb', 'es')

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

# Support potential entry-points console scripts in VENV or not
if [[ ${USE_VENV} = True ]]; then
    PROJECT_VENV["ceilometer"]=${CEILOMETER_DIR}.venv
    CEILOMETER_BIN_DIR=${PROJECT_VENV["ceilometer"]}/bin
else
    CEILOMETER_BIN_DIR=$(get_python_exec_prefix)
fi

function ceilometer_service_url {
    echo "$CEILOMETER_SERVICE_PROTOCOL://$CEILOMETER_SERVICE_HOST:$CEILOMETER_SERVICE_PORT"
}


# _ceilometer_install_mongdb - Install mongodb and python lib.
function _ceilometer_install_mongodb {
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
function _ceilometer_config_apache_wsgi {
    sudo mkdir -p $CEILOMETER_WSGI_DIR

    local ceilometer_apache_conf=$(apache_site_config_for ceilometer)
    local apache_version=$(get_apache_version)
    local venv_path=""

    # Copy proxy vhost and wsgi file
    sudo cp $CEILOMETER_DIR/ceilometer/api/app.wsgi $CEILOMETER_WSGI_DIR/app

    if [[ ${USE_VENV} = True ]]; then
        venv_path="python-path=${PROJECT_VENV["ceilometer"]}/lib/$(python_version)/site-packages"
    fi

    sudo cp $CEILOMETER_DIR/devstack/apache-ceilometer.template $ceilometer_apache_conf
    sudo sed -e "
        s|%PORT%|$CEILOMETER_SERVICE_PORT|g;
        s|%APACHE_NAME%|$APACHE_NAME|g;
        s|%WSGIAPP%|$CEILOMETER_WSGI_DIR/app|g;
        s|%USER%|$STACK_USER|g;
        s|%VIRTUALENV%|$venv_path|g
    " -i $ceilometer_apache_conf
}

# Install required services for storage backends
function _ceilometer_prepare_storage_backend {
    if [ "$CEILOMETER_BACKEND" = 'mongodb' ] ; then
        pip_install_gr pymongo
        _ceilometer_install_mongodb
    fi

    if [ "$CEILOMETER_BACKEND" = 'es' ] ; then
        ${TOP_DIR}/pkg/elasticsearch.sh download
        ${TOP_DIR}/pkg/elasticsearch.sh install
    fi
}


# Create ceilometer related accounts in Keystone
function _ceilometer_create_accounts {
    if is_service_enabled ceilometer-api; then

        create_service_user "ceilometer" "admin"

        get_or_create_service "ceilometer" "metering" "OpenStack Telemetry Service"
        get_or_create_endpoint "metering" \
            "$REGION_NAME" \
            "$(ceilometer_service_url)" \
            "$(ceilometer_service_url)" \
            "$(ceilometer_service_url)"
    fi
}

# Activities to do before ceilometer has been installed.
function preinstall_ceilometer {
    echo_summary "Preinstall not in virtualenv context. Skipping."
}

# Remove WSGI files, disable and remove Apache vhost file
function _ceilometer_cleanup_apache_wsgi {
    if is_service_enabled ceilometer-api && [ "$CEILOMETER_USE_MOD_WSGI" == "True" ]; then
        sudo rm -f "$CEILOMETER_WSGI_DIR"/*
        sudo rmdir "$CEILOMETER_WSGI_DIR"
        sudo rm -f $(apache_site_config_for ceilometer)
    fi
}

function _drop_database {
    if is_service_enabled ceilometer-api ; then
        if [ "$CEILOMETER_BACKEND" = 'mongodb' ] ; then
            mongo ceilometer --eval "db.dropDatabase();"
        elif [ "$CEILOMETER_BACKEND" = 'es' ] ; then
            curl -XDELETE "localhost:9200/events_*"
        fi
    fi
}

# cleanup_ceilometer() - Remove residual data files, anything left over
# from previous runs that a clean run would need to clean up
function cleanup_ceilometer {
    _ceilometer_cleanup_apache_wsgi
    _drop_database
    sudo rm -f "$CEILOMETER_CONF_DIR"/*
    sudo rmdir "$CEILOMETER_CONF_DIR"
}

# Set configuration for storage backend.
function _ceilometer_configure_storage_backend {
    if [ "$CEILOMETER_BACKEND" = 'mysql' ] || [ "$CEILOMETER_BACKEND" = 'postgresql' ] ; then
        iniset $CEILOMETER_CONF database event_connection $(database_connection_url ceilometer)
    elif [ "$CEILOMETER_BACKEND" = 'es' ] ; then
        # es is only supported for events. we will use sql for metering.
        iniset $CEILOMETER_CONF database event_connection es://localhost:9200
        ${TOP_DIR}/pkg/elasticsearch.sh start
    elif [ "$CEILOMETER_BACKEND" = 'mongodb' ] ; then
        iniset $CEILOMETER_CONF database event_connection mongodb://localhost:27017/ceilometer
    else
        die $LINENO "Unable to configure unknown CEILOMETER_BACKEND $CEILOMETER_BACKEND"
    fi
    _drop_database
}

# Configure Ceilometer
function configure_ceilometer {

    local conffile

    iniset $CEILOMETER_CONF DEFAULT debug "$ENABLE_DEBUG_LOG_LEVEL"

    # Install the policy file and declarative configuration files to
    # the conf dir.
    # NOTE(cdent): Do not make this a glob as it will conflict
    # with rootwrap installation done elsewhere and also clobber
    # ceilometer.conf settings that have already been made.
    # Anyway, explicit is better than implicit.
    for conffile in policy.json api_paste.ini; do
        cp $CEILOMETER_DIR/etc/ceilometer/$conffile $CEILOMETER_CONF_DIR
    done

    configure_auth_token_middleware $CEILOMETER_CONF ceilometer $CEILOMETER_AUTH_CACHE_DIR

    # Configure storage
    if is_service_enabled ceilometer-api; then
        _ceilometer_configure_storage_backend
    fi

    if is_service_enabled ceilometer-api && [ "$CEILOMETER_USE_MOD_WSGI" == "True" ]; then
        iniset $CEILOMETER_CONF api pecan_debug "False"
        _ceilometer_config_apache_wsgi
    fi
}

# init_ceilometer() - Initialize etc.
function init_ceilometer {
    # Get ceilometer keystone settings in place
    _ceilometer_create_accounts
    # Create cache dir
    sudo install -d -o $STACK_USER $CEILOMETER_AUTH_CACHE_DIR
    rm -f $CEILOMETER_AUTH_CACHE_DIR/*

    if is_service_enabled ceilometer-api && is_service_enabled mysql postgresql ; then
        if [ "$CEILOMETER_BACKEND" = 'mysql' ] || [ "$CEILOMETER_BACKEND" = 'postgresql' ] || [ "$CEILOMETER_BACKEND" = 'es' ] ; then
            recreate_database ceilometer
            $CEILOMETER_BIN_DIR/ceilometer-dbsync
        fi
    fi
}

# Install Ceilometer.
function install_ceilometer {
    if is_service_enabled ceilometer-api; then
        _ceilometer_prepare_storage_backend
    fi

    setup_develop $CEILOMETER_DIR
    sudo install -d -o $STACK_USER -m 755 $CEILOMETER_CONF_DIR
}

# start_ceilometer() - Start running processes, including screen
function start_ceilometer {
    if [[ "$CEILOMETER_USE_MOD_WSGI" == "False" ]]; then
        run_process ceilometer-api "$CEILOMETER_BIN_DIR/ceilometer-api -d -v --config-file $CEILOMETER_CONF"
    elif is_service_enabled ceilometer-api; then
        enable_apache_site ceilometer
        restart_apache_server
        tail_log ceilometer /var/log/$APACHE_NAME/ceilometer.log
        tail_log ceilometer-api /var/log/$APACHE_NAME/ceilometer_access.log
    fi

    # Only die on API if it was actually intended to be turned on
    if is_service_enabled ceilometer-api; then
        echo "Waiting for ceilometer-api to start..."
        if ! wait_for_service $SERVICE_TIMEOUT $(ceilometer_service_url)/v2/; then
            die $LINENO "ceilometer-api did not start"
        fi
    fi
}

# stop_ceilometer() - Stop running processes
function stop_ceilometer {
    if is_service_enabled ceilometer-api ; then
        if [ "$CEILOMETER_USE_MOD_WSGI" == "True" ]; then
            disable_apache_site ceilometer
            restart_apache_server
        else
            stop_process ceilometer-api
        fi
    fi
}

# This is the main for plugin.sh
if is_service_enabled ceilometer; then
    if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
        # Set up other services
        echo_summary "Configuring system services for Ceilometer"
        preinstall_ceilometer
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing Ceilometer"
        # Use stack_install_service here to account for vitualenv
        stack_install_service ceilometer
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring Ceilometer"
        configure_ceilometer
    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        echo_summary "Initializing Ceilometer"
        # Tidy base for ceilometer
        init_ceilometer
        # Start the services
        start_ceilometer
    fi

    if [[ "$1" == "unstack" ]]; then
        echo_summary "Shutting Down Ceilometer"
        stop_ceilometer
    fi

    if [[ "$1" == "clean" ]]; then
        echo_summary "Cleaning Ceilometer"
        cleanup_ceilometer
    fi
fi

# Restore xtrace
$XTRACE
