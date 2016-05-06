#!/bin/bash
#
#

set -o errexit

source $GRENADE_DIR/grenaderc
source $GRENADE_DIR/functions

source $BASE_DEVSTACK_DIR/functions
source $BASE_DEVSTACK_DIR/stackrc # needed for status directory
source $BASE_DEVSTACK_DIR/lib/tls
source $BASE_DEVSTACK_DIR/lib/apache

# Locate the panko plugin and get its functions
PANKO_DEVSTACK_DIR=$(dirname $(dirname $0))
source $PANKO_DEVSTACK_DIR/plugin.sh

set -o xtrace

stop_panko

# ensure everything is stopped

SERVICES_DOWN="panko-api"

ensure_services_stopped $SERVICES_DOWN
