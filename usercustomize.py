import os.path as op
from importlib.machinery import SourceFileLoader
pundler = SourceFileLoader('pundle', op.join(op.dirname(__file__), 'pundler.py')).load_module()
pundler.install_finder()
print('Pundler loaded')