#!/usr/bin/env bash

# ``upgrade-panko``

echo "*********************************************************************"
echo "Begin $0"
echo "*********************************************************************"

# Clean up any resources that may be in use
cleanup() {
    set +o errexit

    echo "*********************************************************************"
    echo "ERROR: Abort $0"
    echo "*********************************************************************"

    # Kill ourselves to signal any calling process
    trap 2; kill -2 $$
}

trap cleanup SIGHUP SIGINT SIGTERM

# Keep track of the grenade directory
RUN_DIR=$(cd $(dirname "$0") && pwd)

# Source params
. $GRENADE_DIR/grenaderc

# Import common functions
. $GRENADE_DIR/functions

# This script exits on an error so that errors don't compound and you see
# only the first error that occurred.
set -o errexit

# Save mongodb state (replace with snapshot)
# TODO(chdent): There used to be a 'register_db_to_save panko'
# which may wish to consider putting back in.
if grep -q 'connection *= *mongo' /etc/panko/panko.conf; then
    mongodump --db panko --out $SAVE_DIR/panko-dump.$BASE_RELEASE
fi

# Upgrade Panko
# ==================
# Locate panko devstack plugin, the directory above the
# grenade plugin.
PANKO_DEVSTACK_DIR=$(dirname $(dirname $0))

# Get functions from current DevStack
. $TARGET_DEVSTACK_DIR/functions
. $TARGET_DEVSTACK_DIR/stackrc
. $TARGET_DEVSTACK_DIR/lib/apache

# Get panko functions from devstack plugin
. $PANKO_DEVSTACK_DIR/settings

# Print the commands being run so that we can see the command that triggers
# an error.
set -o xtrace

# Install the target panko
. $PANKO_DEVSTACK_DIR/plugin.sh stack install

# calls upgrade-panko for specific release
upgrade_project panko $RUN_DIR $BASE_DEVSTACK_BRANCH $TARGET_DEVSTACK_BRANCH

# Migrate the database
# NOTE(chdent): As we evolve BIN_DIR is likely to be defined, but
# currently it is not.
PANKO_BIN_DIR=$(dirname $(which panko-dbsync))
$PANKO_BIN_DIR/panko-dbsync || die $LINENO "DB sync error"

# Start Panko
start_panko

ensure_services_started panko-api

# Save mongodb state (replace with snapshot)
if grep -q 'connection *= *mongo' /etc/panko/panko.conf; then
    mongodump --db panko --out $SAVE_DIR/panko-dump.$TARGET_RELEASE
fi


set +o xtrace
echo "*********************************************************************"
echo "SUCCESS: End $0"
echo "*********************************************************************"
