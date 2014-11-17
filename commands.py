import sys
import parser
from installs import install_from_scratch, install_by_freeze


def freeze():
    parse = parser.Parser()
    are_freezed_incorrect, freezed_installed = parse.get_unresolved_requirements()
    if not are_freezed_incorrect:
        print('%s have actual information' % parse.freezed_file)
        sys.exit(0)
    print('%s outdated %r' % (parse.freezed_file, [str(c) for c in are_freezed_incorrect]))
    install_from_scratch(parse)



def install():
    parse = parser.Parser()
    are_freezed_incorrect, not_installed = parse.get_unresolved_requirements()
    if are_freezed_incorrect:
        print('%s is outdated. Run `freeze` to actualize and install requirements.' % parse.freezed_file)
        exit(1)
    if not not_installed:
        print('All requirement are installed. Nothing to do.')
        exit(0)
    install_by_freeze(parse)


if __name__ == '__main__':
    freeze()