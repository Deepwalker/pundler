from pundle import Parser


def test_parser(mocker):
    parser_args = {
        'requirements_files': {'': 'requirements.txt'},
        'frozen_files': {'': 'frozen.txt'},
    }
    mocker.patch('pundle.parse_file')
    parser = Parser(**parser_args)
    suite = parser.create_suite()
    print(suite)
