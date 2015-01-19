
# pundler user customization start
import os.path as op
from importlib.machinery import SourceFileLoader
pundler = SourceFileLoader('pundler', op.join(op.dirname(__file__), 'pundler.py')).load_module()


parser_kw = pundler.create_parser_parameters()
if parser_kw:
    suite = pundler.Parser(**parser_kw).create_suite()
    if suite.need_refreeze():
        raise Exception('%s file is outdated' % suite.parser.freezed_file)

    suite.activate_all()
    pundler.global_suite = suite
# pundler user customization end
