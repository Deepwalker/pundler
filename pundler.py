import sys
import os.path as op
from os import makedirs, listdir
import glob
import json
from importlib.machinery import ModuleSpec, SourceFileLoader
from itertools import groupby
from operator import itemgetter
import subprocess
import tempfile
import shutil
from collections import defaultdict
from dl import locators
from dl.util import parse_requirement

default_locator = locators.AggregatingLocator(
                    locators.JSONLocator(),
                    locators.SimpleScrapingLocator('https://pypi.python.org/simple/',
                                          timeout=3.0),
                    scheme='legacy')
locate = default_locator.locate


class CommandFailed(Exception):
    pass
# import logging
# import sys
# root = logging.getLogger()
# root.setLevel(logging.DEBUG)
# ch = logging.StreamHandler(sys.stdout)
# ch.setLevel(logging.DEBUG)
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# ch.setFormatter(formatter)
# root.addHandler(ch)

def group(itr, key):
    return dict((x, [i[1] for i in y]) for x, y in groupby(sorted(itr, key=key), key=key))


class PundlerFinder(object):
    def __init__(self, basepath):
        self.basepath = basepath
        self.pundles = defaultdict(list)
        for line in open('freezed.txt').readlines():
            if not line.strip():
                continue
            if '###' in line:
                pundle = json.loads(line.split('###')[1].strip())
            else:
                pundle = dict(zip(
                    ['name', 'version'],
                    [item.strip() for item in line.split('==')]
                ))
                pundle['top_level'] = [pundle['name']]
            base_dir = op.join('Pundledir', '{name}-{version}'.format(**pundle))
            for top in pundle['top_level']:
                top_pundle = pundle.copy()
                top_pundle['path'] = op.join('Pundledir', '{name}-{version}'.format(**pundle), top)
                if not op.exists(top_pundle['path']):
                    top_pundle['path'] = op.join('Pundledir', '{name}-{version}'.format(**pundle), top + '.py')
                if not op.exists(top_pundle['path']):
                    continue
                self.pundles[top].append(top_pundle)
        print(self.pundles)

    def find_spec(self, fullname, path, target_module):
        if path is not None:
            return None
        if fullname not in self.pundles:
            return None
        pundle = self.pundles[fullname][0]
        if pundle['path'].endswith('.py'):
            path = pundle['path']
            is_package = False
        else:
            path = op.join(pundle['path'], '__init__.py')
            is_package = True
        spec = ModuleSpec(fullname, SourceFileLoader(fullname, path), origin=path, is_package=is_package)
        if is_package:
            spec.submodule_search_locations = [pundle['path']]
        return spec

def install_finder():
    sys.meta_path.insert(0, PundlerFinder('.'))



def require_pundledir():
    if not op.exists('Pundledir'):
        makedirs('Pundledir')

def parse_requirements(requirements):
    def inner_parse(reqs):
        for req in reqs:
            parsed = parse_requirement(req)
            yield (parsed.name.lower(), parsed.constraints or [])
            dist = locate(req)
            if not dist:
                dist = locate(req, prereleases=True)
                if not dist:
                    raise Exception('Distribution for %s was not found' % req)
            yield from inner_parse(dist.run_requires)
    reqs = [(name, ','.join(''.join(x) for vers in versions for x in vers)) 
        for name, versions in group(inner_parse(requirements), itemgetter(0)).items()]
    return [locate(' '.join(req), prereleases=True) for req in reqs]


def get_installed():
    return group([item.split('-', 1) for item in listdir('Pundledir')], itemgetter(0))


def install(dist):
    name = dist.name
    tmpdir = tempfile.mkdtemp()
    print(name)
    res = subprocess.call([sys.executable,
        '-m', 'pip', 'install',
        '--no-deps',
        '--install-option=%s' % ('--install-scripts=%s' % op.join(tmpdir, '.scripts')),
        '-t', tmpdir,
        '%s==%s'%(name, dist.version)
    ])
    if res != 0:
        raise Exception('%s was not installed due error' % name)
    print(tmpdir)
    dir_name = '{}-{}'.format(name.lower(), dist.version)
    target_dir = op.join('Pundledir', dir_name)
    try:
        makedirs(target_dir)
    except FileExistsError:
        pass
    for item in listdir(tmpdir):
        shutil.move(op.join(tmpdir, item), op.join(target_dir, item))
    shutil.rmtree(tmpdir)


def install_requirements():
    require_pundledir()
    installed = get_installed()
    if not op.isfile('requirements.txt'):
        raise Exception('File requirements.txt not found')
    requirements = [line.strip() for line in open('requirements.txt').readlines() if line.strip() and not line.startswith('#')]
    dists = parse_requirements(requirements)
    for dist in dists:
        if not dist.version in installed.get(dist.name.lower(), []):
            install(dist)
        # provided top levels
        top_level = glob.glob('Pundledir/{}-{}/*-info/top_level.txt'.format(dist.name.lower(), dist.version))
        dist.top_level = set([dist.name.lower()])
        if top_level:
            dist.top_level = dist.top_level.union(set([line.strip() for line in open(top_level[0]) if line.strip()]))

    # Create freezed version
    with open('freezed.txt', 'w') as f:
        dists.sort(key=lambda d: d.name)
        for dist in dists:
            meta = json.dumps({
                'top_level': list(dist.top_level),
                'name': dist.key,
                'version': dist.version
            })
            f.write('{dist.key}=={dist.version} ### {meta}\n'.format(dist=dist, meta=meta))
        f.write('\n')


def test():
    install_finder()
    import opster
    import trafaret
    from trafaret import extras
    import jinja2 as j
    print(repr(j))

if __name__ == '__main__':
    install_requirements()