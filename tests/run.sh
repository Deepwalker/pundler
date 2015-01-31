#! /bin/bash

export PUNDLERDIR="pundlerdir"
rm -r $PUNDLERDIR
rm requirements.txt
rm frozen.txt

bats base.sh

rm -r $PUNDLERDIR
rm requirements.txt
rm frozen.txt