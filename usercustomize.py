import os.path as op
from importlib.machinery import SourceFileLoader
# finder = SourceFileLoader('finder', op.join(op.dirname(__file__), 'finder.py')).load_module()
# finder.install_finder()
# print('Finder loaded')
pundler = SourceFileLoader('pundler', op.join(op.dirname(__file__), 'parser.py')).load_module()
suite = pundler.Parser().create_suite()
if suite.need_refreeze():
    raise Exception('%s file is outdated' % suite.parser.freezed_file)

suite.activate_all()