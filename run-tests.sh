#!/bin/bash

set -e
set -o pipefail

# Run unit test
export OS_TEST_PATH=panko/tests/unit
stestr run $*

# Run functional test
export OS_TEST_PATH=panko/tests/functional/
for backend in $PANKO_BACKENDS; do
    pifpaf run $backend -- stestr run $*
done
