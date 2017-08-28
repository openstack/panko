#!/bin/bash
#
#

set -o errexit

. $GRENADE_DIR/grenaderc
. $GRENADE_DIR/functions

. $BASE_DEVSTACK_DIR/functions
. $BASE_DEVSTACK_DIR/stackrc # needed for status directory
. $BASE_DEVSTACK_DIR/lib/tls
. $BASE_DEVSTACK_DIR/lib/apache

# Locate the panko plugin and get its functions
PANKO_DEVSTACK_DIR=$(dirname $(dirname $0))
. $PANKO_DEVSTACK_DIR/plugin.sh

set -o xtrace

stop_panko

# ensure everything is stopped

SERVICES_DOWN="panko-api"

ensure_services_stopped $SERVICES_DOWN
