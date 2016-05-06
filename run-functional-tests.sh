#!/bin/bash -x
set -e
# Use a mongodb backend by default

if [ -z $PANKO_TEST_BACKEND ]; then
    PANKO_TEST_BACKEND="mongodb"
fi

for backend in $PANKO_TEST_BACKEND; do
    pifpaf run $backend ./tools/pretty_tox.sh $*
done
