from __future__ import print_function#, unicode_literals
import re
try:
    from urllib.parse import urlparse
except ImportError:
    import urlparse
from collections import defaultdict
import platform
import os.path as op
import os
from os import makedirs
import tempfile
import shutil
import subprocess
import sys
import shlex
import pkg_resources

# TODO bundle own version of distlib. Perhaps
try:
    from pip._vendor.distlib.locators import locate
except ImportError:
    from pip.vendor.distlib.locators import locate

try:
    str_types = (basestring,)
except NameError:
    str_types = (str, bytes)

def print_message(*a, **kw):
    print(*a, **kw)


def python_version_string():
    version_info = sys.pypy_version_info if platform.python_implementation() == 'PyPy' else sys.version_info
    version_string = '{v.major}.{v.minor}.{v.micro}'.format(v=version_info)
    build, _ = platform.python_build()
    return '{}-{}-{}'.format(platform.python_implementation(), version_string, build)


def parse_file(filename):
    return [req[0] for req in 
        filter(None, [shlex.split(line)
            for line in open(filename) if line.strip() and not line.startswith('#')
        ])
    ]


def test_vcs(req):
    return '+' in req and req.index('+') == 3


class CustomReq(object):
    def __init__(self, line, source=None):
        self.line = line
        if isinstance(line, pkg_resources.Requirement):
            self.req = line
        elif not test_vcs(line):
            self.req = pkg_resources.Requirement.parse(line)
        else:
            parsed_url = urlparse(line)
            if not (parsed_url.fragment and parsed_url.fragment.startswith('egg=')):
                raise Exception('Bad url %r' % line)
            self.egg = parsed_url.fragment.split('=', 1)[1]
            self.req = None
        self.source = source

    def __contains__(self, something):
        return (something in self.req) if self.req else False

    def __repr__(self):
        return '<CustomReq %r>' % self.__dict__

    def why_str(self):
        if isinstance(self.source, str_types):
            return '{} << {}'.format(self.line, self.source)
        if isinstance(self.source, CustomReq):
            return '{} << {}'.format(self.line, self.source.why_str())
        return '?'

    def adjust_with_req(self, req):
        if not self.req:
            raise Exception('VCS')
        versions = ','.join(''.join(t) for t in set(self.req.specs + req.req.specs))
        self.requirement = pkg_resources.Requirement.parse('{} {}'.format(
            self.req.project_name, versions
        ))

    @property
    def key(self):
        return self.req.key if self.req else self.egg

    def locate(self):
        dist = locate(str(self.req))
        if not dist:
            dist = locate(str(self.req), prereleases=True)
        return dist

    def locate_and_install(self, suite, installed=None):
        loc_dist = self.locate()
        ready = [installation for installation in (installed or []) if installation.version == loc_dist.version]
        if ready:
            return ready[0]
        target_dir = op.join(suite.parser.directory, '{}-{}'.format(loc_dist.key, loc_dist.version))
        try:
            makedirs(target_dir)
        except OSError:
            pass
        tmp_dir = tempfile.mkdtemp()
        try:
            res = subprocess.call([sys.executable,
                '-m', 'pip', 'install',
                '--no-deps',
                '--install-option=%s' % ('--install-scripts=%s' % op.join(tmp_dir, '.scripts')),
                '-t', tmp_dir,
                '%s==%s'%(loc_dist.name, loc_dist.version)
            ])
            for item in os.listdir(tmp_dir):
                shutil.move(op.join(tmp_dir, item), op.join(target_dir, item))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        if res != 0:
            raise Exception('%s was not installed due error' % loc_dist.name)
        return next(iter(pkg_resources.find_distributions(target_dir, True)), None)


class RequirementState(object):
    def __init__(self, key, req=None, frozen=None, installed=None):
        self.key = key
        self.requirement = req
        self.frozen = frozen
        self.installed = installed or []
        self.installed.sort()
        self.installed.reverse()

    def __repr__(self):
        return '<RequirementState %r>' % self.__dict__

    def adjust_with_req(self, req):
        if self.requirement:
            self.requirement.adjust_with_req(req)
        else:
            self.requirement = req

    def has_correct_freeze(self):
        return self.requirement and self.frozen and self.frozen in self.requirement

    def check_installed_version(self, suite, install=False):
        # install version of package if not installed
        dist = None
        if self.has_correct_freeze():
            dist = [installation for installation in self.installed if installation.version == self.frozen]
            dist = dist[0] if dist else None
            if install and not dist:
                dist = self.install_frozen(suite)
        if install and not dist:
            dist = self.requirement.locate_and_install(suite, installed=self.get_installed())
            self.frozen = dist.version
            self.installed.append(dist)
            self.frozen = dist.version
        return dist

    def get_installed(self):
        return [installation for installation in self.installed if installation.version in self.requirement]

    def upgrade(self, suite):
        # check if we have fresh packages on PIPY
        dists = self.get_installed()
        dist = dists[0] if dists else None
        latest = self.requirement.locate()
        if not dist or pkg_resources.parse_version(latest.version) > pkg_resources.parse_version(dist.version):
            print_message('Upgrade to', latest)
            dist = self.requirement.locate_and_install(suite)
        # Anyway use latest available dist
        self.frozen = dist.version
        self.installed.append(dist)
        return dist

    def reveal_requirements(self, suite, install=False, upgrade=False):
        if upgrade:
            dist = self.upgrade(suite)
        else:
            dist = self.check_installed_version(suite, install=install)
        if not dist:
            return
        for req in dist.requires():
            suite.adjust_with_req(CustomReq(str(req), source=self.requirement), install=install, upgrade=upgrade)

    def frozen_dump(self):
        main = '{}=={}'.format(self.key, self.frozen)
        comment = self.requirement.why_str()
        return '{:20s} # {}'.format(main, comment)

    def frozen_dist(self):
        for dist in self.installed:
            if dist.version == self.frozen:
                return dist

    def install_frozen(self, suite):
        if self.frozen_dist() or not self.frozen:
            return
        frozen_req = CustomReq("{}=={}".format(self.key, self.frozen))
        dist = frozen_req.locate_and_install(suite)
        self.installed.append(dist)
        return dist

    def activate(self):
        dist = self.frozen_dist()
        if not dist:
            raise Exception('Distribution is not installed %s' % self.key)
        dist.activate()
        pkg_resources.working_set.add_entry(dist.location)
        # find end execute pth
        for filename in os.listdir(dist.location):
            if not filename.endswith('pth'):
                continue
            try:
                for line in open(op.join(dist.location, filename)):
                    if line.startswith('import '):
                        sitedir = dist.location
                        # print('Exec', line.strip())
                        exec(line.strip())
            except Exception as e:
                print('Erroneous pth file %r' % op.join(dist.location, filename))
                print(e)


class Suite(object):
    def __init__(self, parser):
        self.states = {}
        self.parser = parser

    def add(self, key, state):
        self.states[key] = state

    def __repr__(self):
        return '<Suite %r>' % self.states

    def required_states(self):
        return [state for state in self.states.values() if state.requirement]

    def need_freeze(self):
        self.install(install=False)
        not_correct = not all(state.has_correct_freeze() for state in self.required_states())
        # TODO
        # unneeded = any(state.frozen for state in self.states.values() if not state.requirement)
        # if unneeded:
        #     print('!!! Unneeded', [state.key for state in self.states.values() if not state.requirement])
        return not_correct #or unneeded

    def adjust_with_req(self, req, install=False, upgrade=False):
        state = self.states.get(req.key)
        if not state:
            state = RequirementState(req.key, req=req)
            self.add(req.key, state)
        else:
            state.adjust_with_req(req)
        state.reveal_requirements(self, install=install, upgrade=upgrade)

    def install(self, install=True):
        for state in self.required_states():
            state.reveal_requirements(self, install=install)

    def upgrade(self, key=None):
        states = [self.states[key]] if key else self.required_states()
        for state in states:
            state.reveal_requirements(self, upgrade=True)

    def dump_frozen(self):
        return '\n'.join(sorted(
            state.frozen_dump() for state in self.required_states() if state.requirement
        )) + '\n'

    def need_install(self):
        return not all(state.frozen_dist() for state in self.states.values() if state.frozen)

    def install_frozen(self):
        for state in self.states.values():
            state.install_frozen(self)

    def activate_all(self):
        for state in self.required_states():
            if state.requirement:
                state.activate()



class Parser(object):
    def __init__(self, directory='Pundledir', requirements_file='requirements.txt', frozen_file='frozen.txt'):
        self.directory = directory
        self.requirements_file = requirements_file
        self.frozen_file = frozen_file

    def create_suite(self):
        reqs, freezy, diry = self.parse_requirements(), self.parse_frozen(), self.parse_directory()
        state_keys = set(list(reqs.keys()) + list(freezy.keys()) + list(diry.keys()))
        suite = Suite(self)
        for key in state_keys:
            suite.add(key,
                RequirementState(key, reqs.get(key), freezy.get(key), diry.get(key, []))
            )
        return suite

    def parse_directory(self):
        if not op.exists(self.directory):
            return {}
        dists = [next(iter(
                pkg_resources.find_distributions(op.join(self.directory, item), True)
            ), None) for item in os.listdir(self.directory) if '-' in item]
        dists = filter(None, dists)
        result = defaultdict(list)
        for dist in dists:
            result[dist.key].append(dist)
        return result

    def parse_frozen(self):
        frozen = [line.split('==') for line in parse_file(self.frozen_file)] if op.exists(self.frozen_file) else []
        frozen_versions = dict((name.lower(), version) for name, version in frozen)
        return frozen_versions

    def parse_requirements(self):
        requirements = parse_file(self.requirements_file) if op.exists(self.requirements_file) else []
        return dict((req.key, req) for req in (CustomReq(line, 'requirements file') for line in requirements))


# Utilities
def search_files_upward(start_path=None):
    "Search for requirements.txt upward"
    if not start_path:
        start_path = op.abspath(op.curdir)
    if op.exists(op.join(start_path, 'requirements.txt')):
        return start_path
    up_path = op.abspath(op.join(start_path, '..'))
    if op.samefile(start_path, up_path):
        return None
    return search_files_upward(start_path=up_path)


def create_parser_parameters():
    base_path = search_files_upward()
    if not base_path:
        return None
    py_version_path = python_version_string()
    pundledir_base = os.environ.get('PUNDLEDIR') or op.join(op.expanduser('~'), '.pundledir')
    return {
        'requirements_file': op.join(base_path, 'requirements.txt'),
        'frozen_file': op.join(base_path, 'frozen.txt'),
        'directory': op.join(pundledir_base, py_version_path)
    }


def create_parser_or_exit():
    parser_kw = create_parser_parameters()
    if not parser_kw:
        print_message('You have not requirements.txt. Create it and run again.')
        exit(1)
    return parser_kw


# Commands
def upgrade_all(*a, **kw):
    key = kw.pop('key')
    suite = Parser(*a, **kw).create_suite()
    suite.upgrade(key=key)
    suite.install()
    with open(suite.parser.frozen_file, 'w') as f:
        f.write(suite.dump_frozen())


def install_all(*a, **kw):
    suite = Parser(*a, **kw).create_suite()
    if suite.need_freeze() or suite.need_install():
        print_message('Install some packages')
        suite.install()
    else:
        print_message('Nothing to do, all packages installed')
    with open(suite.parser.frozen_file, 'w') as f:
        f.write(suite.dump_frozen())
    return suite



def activate():
    parser_kw = create_parser_parameters()
    if parser_kw:
        suite = Parser(**parser_kw).create_suite()
        if suite.need_freeze():
            raise Exception('%s file is outdated' % suite.parser.frozen_file)
        if suite.need_install():
            raise Exception('Some dependencies not installed')
        suite.activate_all()


FIXATE_TEMPLATE = """
# pundle user customization start
import pundle; pundle.activate()
# pundle user customization end
"""


def fixate():
    print_message('Fixate')
    import site
    userdir = site.getusersitepackages()
    if not userdir:
        raise Exception('Can`t fixate due user have not site package directory')
    try:
        makedirs(userdir)
    except OSError:
        pass
    template = FIXATE_TEMPLATE.replace('op.dirname(__file__)', "'%s'" % op.abspath(op.dirname(__file__)))
    usercustomize_file = op.join(userdir, 'usercustomize.py')
    print_message('Will edit %s file' % usercustomize_file)
    if op.exists(usercustomize_file):
        content = open(usercustomize_file).read()
        if '# pundle user customization start' in content:
            regex = re.compile(r'\n# pundle user customization start.*# pundle user customization end\n', re.DOTALL)
            content, res = regex.subn(template, content)
            open(usercustomize_file, 'w').write(content)
        else:
            open(usercustomize_file, 'a').write(content)
    else:
        open(usercustomize_file, 'w').write(template)
    link_file = op.join(userdir, 'pundle.py')
    if op.lexists(link_file):
        print_message('Remove exist link to pundle')
        os.unlink(link_file)
    print_message('Create link to pundle %s' % link_file)
    os.symlink(op.abspath(__file__), link_file)
    print_message('Complete')


def entry_points():
    parser_kw = create_parser_parameters()
    suite = Parser(**parser_kw).create_suite()
    if suite.need_freeze():
        raise Exception('%s file is outdated' % suite.parser.frozen_file)
    suite.activate_all()
    entries = {}
    for r in suite.states.values():
        d = r.frozen_dist()
        if not d:
            continue
        scripts = d.get_entry_map().get('console_scripts', {})
        for name in scripts:
            entries[name] = d
    return entries


def execute(interpreter, cmd, args):
    # TODO proof implementation
    # clean it
    entries = entry_points()
    exc = entries[cmd].get_entry_info('console_scripts', cmd).load(require=False)
    sys.argv = [cmd] + args
    exc()


def main():
    # I think better have pundledir in special home user directory
    if len(sys.argv) == 1 or sys.argv[1] == 'install':
        install_all(**create_parser_or_exit())

    elif sys.argv[1] == 'upgrade':
        key = sys.argv[2] if len(sys.argv) > 2 else None
        upgrade_all(key=key, **create_parser_or_exit())

    elif sys.argv[1] == 'fixate':
        fixate()

    elif sys.argv[1] == 'exec':
        execute(sys.argv[0], sys.argv[2], sys.argv[3:])

    elif sys.argv[1] == 'entry_points':
        for entry, package in entry_points().items():
            print('%s (%s)' % (entry, package))

    elif sys.argv[1] == 'edit':
        parser_kw = create_parser_parameters()
        suite = Parser(**parser_kw).create_suite()
        if suite.need_freeze():
            raise Exception('%s file is outdated' % suite.parser.frozen_file)
        print(suite.states[sys.argv[2]].frozen_dist().location)

    elif sys.argv[1] == 'console':
        import code; code.InteractiveConsole(locals=globals()).interact();

if __name__ == '__main__':
    main()