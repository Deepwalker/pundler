#! /bin/bash

export PUNDLEDIR="pundledir"
rm -r $PUNDLEDIR

bats base.sh

rm -r $PUNDLEDIR