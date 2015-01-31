#! /bin/bash

export PUNDLERDIR="pundlerdir"
rm -r $PUNDLERDIR

bats base.sh

rm -r $PUNDLERDIR