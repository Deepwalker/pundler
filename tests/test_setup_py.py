from pundle import create_parser

from .lib import fake_parse


PARSER_ARGS = {
    'requirements_files': None,
    'frozen_files': {'': 'frozen.txt'},
    'package': '.',
}


def test_parse_setup_need_freeze(mocker):
    parse_file = fake_parse({
        'frozen.txt': [],
        './frozen_objectid.txt': [],
    })
    setup_data = {
        'install_requires': ['trafaret'],
        'extras_require': {
            'objectid': ['mongodb']
        },
    }
    mocker.patch('pundle.parse_file', new_callable=lambda: parse_file)
    mocker.patch('pundle.op.exists')
    mocker.patch('pundle.os.listdir')
    mocker.patch('pundle.get_info_from_setup', new_callable=lambda: (lambda x: setup_data))
    parser = create_parser(**PARSER_ARGS)
    suite = parser.create_suite()
    print(suite)
    assert suite.need_freeze() == True


def test_parse_setup_frozen(mocker):
    parse_file = fake_parse({
        'frozen.txt': ['trafaret==0.1.1'],
        './frozen_objectid.txt': ['mongodb==0.1.0'],
    })
    setup_data = {
        'install_requires': ['trafaret'],
        'extras_require': {
            'objectid': ['mongodb']
        },
    }
    mocker.patch('pundle.parse_file', new_callable=lambda: parse_file)
    mocker.patch('pundle.op.exists')
    mocker.patch('pundle.os.listdir')
    mocker.patch('pundle.get_info_from_setup', new_callable=lambda: (lambda x: setup_data))
    parser = create_parser(**PARSER_ARGS)
    suite = parser.create_suite()
    print(suite)
    assert suite.need_freeze() == False
    assert suite.need_install() == True
