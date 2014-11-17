import os.path as op
from importlib.machinery import SourceFileLoader
finder = SourceFileLoader('finder', op.join(op.dirname(__file__), 'finder.py')).load_module()
finder.install_finder()
print('Finder loaded')