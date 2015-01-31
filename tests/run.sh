#! /bin/bash

export PUNDLERDIR="pundlerdir"
rm -r $PUNDLERDIR
rm requirements.txt
rm freezed.txt

bats base.sh

rm -r $PUNDLERDIR
rm requirements.txt
rm freezed.txt