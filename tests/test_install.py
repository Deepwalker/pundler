from pundle import Parser

from .lib import fake_parse


PARSER_ARGS = {
    'requirements_files': {'': 'requirements.txt'},
    'frozen_files': {'': 'frozen.txt'},
}


def test_need_freeze(mocker):
    parse_file = fake_parse({
        'requirements.txt': ['trafaret'],
        'frozen.txt': [],
    })
    mocker.patch('pundle.parse_file', new_callable=lambda: parse_file)
    mocker.patch('pundle.op.exists')
    mocker.patch('pundle.os.listdir')
    parser = Parser(**PARSER_ARGS)
    suite = parser.create_suite()
    print(suite)
    assert suite.need_freeze() == True


def test_frozen(mocker):
    parse_file = fake_parse({
        'requirements.txt': ['trafaret'],
        'frozen.txt': ['trafaret==0.1'],
    })
    mocker.patch('pundle.parse_file', new_callable=lambda: parse_file)
    mocker.patch('pundle.op.exists')
    mocker.patch('pundle.os.listdir')
    parser = Parser(**PARSER_ARGS)
    suite = parser.create_suite()
    print(suite)
    assert suite.need_freeze() == False
    assert suite.need_install() == True


def test_vcs(mocker):
    parse_file = fake_parse({
        'requirements.txt': ['git+https://github.com/karanlyons/django-save-the-change@e48502d2568d76bd9c7093f4c002a5b0061bc468#egg=django-save-the-change'],
        'frozen.txt': [],
    })
    mocker.patch('pundle.parse_file', new_callable=lambda: parse_file)
    mocker.patch('pundle.op.exists')
    mocker.patch('pundle.os.listdir')
    parser = Parser(**PARSER_ARGS)
    suite = parser.create_suite()
    print(suite)
    assert suite.need_freeze() == True


def test_vcs_frozen(mocker):
    parse_file = fake_parse({
        'requirements.txt': ['git+https://github.com/karanlyons/django-save-the-change@e48502d2568d76bd9c7093f4c002a5b0061bc468#egg=django-save-the-change'],
        'frozen.txt': ['git+https://github.com/karanlyons/django-save-the-change@e48502d2568d76bd9c7093f4c002a5b0061bc468#egg=django-save-the-change'],
    })
    mocker.patch('pundle.parse_file', new_callable=lambda: parse_file)
    mocker.patch('pundle.op.exists')
    mocker.patch('pundle.os.listdir')
    parser = Parser(**PARSER_ARGS)
    suite = parser.create_suite()
    print(suite)
    assert suite.need_freeze() == False
    assert suite.need_install() == True
