#! /usr/bin/env bats


@test "Install using pundle" {
    echo "trafaret==0.5.2" > requirements.txt
    run python ../pundle.py install
    [ "$status" -eq 0 ]
    [ -d "$PUNDLEDIR" ]
    run ls $PUNDLEDIR/*/trafaret-0.5.2
    [ "$status" -eq 0 ]

    [ -e frozen.txt ]
}

@test "Install one more package using pundle" {
    echo -e "trafaret==0.5.2\nnomad==1.8" > requirements.txt
    run python ../pundle.py install
    [ "$status" -eq 0 ]
    run ls $PUNDLEDIR/*/nomad-1.8
    [ "$status" -eq 0 ]
}

@test "Upgrade package" {
    # Install old version
    echo -e "trafaret==0.5.2\nnomad==1.8" > requirements.txt
    run python ../pundle.py install
    [ "$status" -eq 0 ]
    [[ "$(cat frozen.txt)" =~ "nomad==1.8" ]]

    # And upgrade to new version
    echo -e "trafaret==0.5.2\nnomad==1.11" > requirements.txt
    python ../pundle.py upgrade
    [ "$?" -eq 0 ]
    run ls $PUNDLEDIR/*/nomad-1.11
    [ "$status" -eq 0 ]
    [[ "$(cat frozen.txt)" =~ "nomad==1.11" ]]
}

@test "Check entry point for nomad" {
    echo -e "nomad==1.11" > requirements.txt
    run python ../pundle.py install
    [ "$status" -eq 0 ]

    run python ../pundle.py entry_points
    [ "$status" -eq 0 ]
    [[ "$lines{0}" =~ "nomad" ]]
    [[ "$lines{0}" =~ "1.11" ]]
}

@test "Check import frozen package in python" {
    echo -e "trafaret" > requirements.txt
    run python ../pundle.py install
    [ "$status" -eq 0 ]

    export PYTHONPATH=..:$PYTHONPATH
    run python -c "import pundle; pundle.Parser(**pundle.create_parser_parameters()).create_suite().activate_all(); import trafaret"
    [ "$status" -eq 0 ]
}

@test "Check pip styled git url" {
    echo -e "git+https://github.com/mitsuhiko/jinja2.git@85820fceb83569df62fa5e6b9b0f2f76b7c6a3cf#egg=jinja2-2.8.0" > requirements.txt
    run python ../pundle.py install
    [ "$status" -eq 0 ]
    [[ "$(cat frozen.txt)" =~ "jinja2" ]]
}



function teardown() {
    rm requirements.txt
    rm frozen.txt
}
