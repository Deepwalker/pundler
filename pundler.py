import sys
import os.path as op
from os import makedirs, listdir
import platform
import glob
import json
from importlib.machinery import ModuleSpec, SourceFileLoader
from itertools import groupby
from operator import itemgetter
import subprocess
import tempfile
import shutil
from collections import defaultdict
from pip.vcs import VcsSupport

distlib = SourceFileLoader('distlib', op.join(op.dirname(__file__), 'distlib/distlib/__init__.py')).load_module()
locators = SourceFileLoader('distlib.locators', op.join(op.dirname(__file__), 'distlib/distlib/locators.py')).load_module()
# from distlib import locators
distlib_utils = SourceFileLoader('distlib.util', op.join(op.dirname(__file__), 'distlib/distlib/util.py')).load_module()
# from distlib.util import parse_requirement
parse_requirement = distlib_utils.parse_requirement

default_locator = locators.AggregatingLocator(
                    locators.JSONLocator(),
                    locators.SimpleScrapingLocator('https://pypi.python.org/simple/',
                                          timeout=3.0),
                    scheme='legacy')
locate = default_locator.locate

PYTHON_VERSION = '%s' % platform.python_implementation()


class DistProxy(object):
    def __init__(self, dist):
        self.dist = dist
        self.toplevel = None

    def name(self):
        return self.dist.name

    def lower_name(self):
        return self.dist.name.lower()

    def dir_name(self):
        return '{}-{}'.format(self.lower_name(), self.dist.version)

    def version(self):
        return self.dist.version

    def path(self):
        return self.dir_name()

    def run_requires(self):
        return self.dist.run_requires

    @property
    def freezed_str(self):
        return '{lower_name}=={version}'.format(lower_name=self.lower_name(), version=self.version())

    def top_level(self):
        if self.toplevel != None:
            return self.toplevel
        self.toplevel = set([self.lower_name()])
        top_level = glob.glob(
            'Pundledir/{}/*-info/top_level.txt'.format(self.dir_name())
        )
        if top_level:
            self.toplevel = self.toplevel.union(set([
                line.strip() for line in open(top_level[0]) if line.strip()
            ]))
        return self.toplevel

    def install(self):
        target_dir = op.join('Pundledir', self.dir_name())
        try:
            makedirs(target_dir)
        except FileExistsError:
            pass
        res = subprocess.call([sys.executable,
            '-m', 'pip', 'install',
            '--no-deps',
            '--install-option=%s' % ('--install-scripts=%s' % op.join(target_dir, '.scripts')),
            '-t', target_dir,
            '%s==%s'%(self.name(), self.version())
        ])
        if res != 0:
            raise Exception('%s was not installed due error' % self.name())


vcs_support = VcsSupport()
class VcsProxy(object):
    @classmethod
    def is_vcs(cls, req):
        if not '+' in req:
            return False
        schema, url = req.split('+', 1)
        if schema in vcs_support.schemes:
            return True

    def __init__(self, src):
        self.schema, self.url = src.split('+', 1)
        # self.backend = vcs_support.get_backend(self.schema)(src)
        # self.tmpdir = tmpfile.tmpdir
        # self.backend.obtain(self.tmpdir)


def group(itr, key):
    return dict((x, [i[1] for i in y]) for x, y in groupby(sorted(itr, key=key), key=key))


def require_pundledir():
    if not op.exists('Pundledir'):
        makedirs('Pundledir')

def parse_requirements():
    def inner_parse(reqs):
        for req in reqs:
            if VcsProxy.is_vcs(req):
                dist = VcsProxy(req)
            else:
                parsed = parse_requirement(req)
                yield (parsed.name.lower(), parsed.constraints or [])
                dist = locate(req)
                if not dist:
                    dist = locate(req, prereleases=True)
                    if not dist:
                        raise Exception('Distribution for %s was not found' % req)
                dist = DistProxy(dist)
            for sub_dist in inner_parse(dist.run_requires()):
                yield sub_dist

    if not op.isfile('requirements.txt'):
        raise Exception('File requirements.txt not found')
    requirements = [line.strip() for line in open('requirements.txt').readlines()
                    if line.strip() and not line.startswith('#')]
    reqs = [(name, ','.join(''.join(x) for vers in versions for x in vers)) 
        for name, versions in group(inner_parse(requirements), itemgetter(0)).items()]
    return [DistProxy(locate(' '.join(req), prereleases=True)) for req in reqs]


def get_installed():
    return group([item.split('-', 1) for item in listdir('Pundledir')], itemgetter(0))


def write_freezed(dists):
    # Create freezed version
    with open('freezed.txt', 'w') as f:
        dists.sort(key=lambda d: d.name())
        for dist in dists:
            meta = json.dumps({
                'top_level': list(sorted(dist.top_level())),
                'name': dist.lower_name(),
                'version': dist.version(),
                'path': dist.path()
            }, sort_keys=True)
            f.write('{dist.freezed_str:30s} ### {meta}\n'.format(dist=dist, meta=meta))
        f.write('\n')


def install_requirements():
    require_pundledir()
    installed = get_installed()
    dists = parse_requirements()
    for dist in dists:
        if not dist.version() in installed.get(dist.lower_name(), []):
            dist.install()
    write_freezed(dists)


if __name__ == '__main__':
    install_requirements()