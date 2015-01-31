#! /usr/bin/env bats


@test "Install using pundler" {
    echo "trafaret==0.5.2" > requirements.txt
    run python ../pundler.py install
    [ "$status" -eq 0 ]
    [ -d "$PUNDLERDIR" ]
    run ls $PUNDLERDIR/*/trafaret-0.5.2
    [ "$status" -eq 0 ]

    [ -e frozen.txt ]
}

@test "Install one more package using pundler" {
    echo -e "trafaret==0.5.2\nnomad==1.8" > requirements.txt
    run python ../pundler.py install
    [ "$status" -eq 0 ]
    run ls $PUNDLERDIR/*/nomad-1.8
    [ "$status" -eq 0 ]
}

@test "Upgrade package" {
    echo -e "trafaret==0.5.2\nnomad" > requirements.txt
    python ../pundler.py upgrade
    [ "$?" -eq 0 ]
    run ls $PUNDLERDIR/*/nomad-1.9
    [ "$status" -eq 0 ]
}