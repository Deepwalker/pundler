from __future__ import print_function#, unicode_literals
import re
try:
    from urllib.parse import urlparse, parse_qsl
except ImportError:
    import urlparse
    parse_qsl = urlparse.parse_qsl
from collections import defaultdict
from base64 import b64encode, b64decode
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
    from pip._vendor.distlib import locators
except ImportError:
    from pip.vendor.distlib import locators

try:
    str_types = (basestring,)
except NameError:
    str_types = (str, bytes)

def print_message(*a, **kw):
    print(*a, **kw)


class PundleException(Exception):
    pass


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


def parse_vcs_requirement(req):
    if not '+' in req:
        return None
    vcs, url = req.split('+', 1)
    if not vcs in ('git', 'svn', 'hg'):
        return None
    parsed_url = urlparse(url)
    parsed = dict(parse_qsl(parsed_url.fragment))
    if not 'egg' in parsed:
        return None
    return parsed['egg'].split('-')[0], req


class VCSDist(object):
    def __init__(self, directory):
        self.dir = directory
        name = op.split(directory)[-1]
        self.key, encoded = name.split('+', 1)
        self.line = b64decode(encoded).decode('utf-8')
        self.version = self.line
        self.pkg_resource = next(iter(pkg_resources.find_distributions(self.dir, True)), None)
        self.location = self.pkg_resource.location

    def requires(self, extras=[]):
        return self.pkg_resource.requires(extras=extras)

    def activate(self):
        return self.pkg_resource.activate()


class CustomReq(object):
    def __init__(self, line, source=None):
        self.line = line
        self.egg = None
        if isinstance(line, pkg_resources.Requirement):
            self.req = line
        elif test_vcs(line):
            res = parse_vcs_requirement(line)
            if not res:
                raise PundleException('Bad url %r' % line)
            key, version = res
            self.egg = key
            self.req = None
        else:
            self.req = pkg_resources.Requirement.parse(line)
        self.source = source

    def __contains__(self, something):
        if self.req:
            return (something in self.req)
        elif self.egg:
            return something == self.line
        else:
            return False

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
            raise PundleException('VCS')
        versions = ','.join(''.join(t) for t in set(self.req.specs + req.req.specs))
        self.requirement = pkg_resources.Requirement.parse('{} {}'.format(
            self.req.project_name, versions
        ))

    @property
    def key(self):
        return self.req.key if self.req else self.egg

    @property
    def extras(self):
        return self.req.extras if self.req else []

    def locate(self, suite):
        dist = suite.locate(str(self.req))
        if not dist:
            dist = suite.locate(str(self.req), prereleases=True)
        if not dist:
            raise PundleException('%s can not be located' % self.req)
        return dist

    def locate_and_install(self, suite, installed=None):
        if self.egg:
            key = b64encode(self.line.encode('utf-8')).decode()
            target_dir = op.join(suite.parser.directory, '{}+{}'.format(self.egg, key))
            target_req = self.line
        else:
            loc_dist = self.locate(suite)
            ready = [installation for installation in (installed or []) if installation.version == loc_dist.version]
            if ready:
                return ready[0]
            target_dir = op.join(suite.parser.directory, '{}-{}'.format(loc_dist.key, loc_dist.version))
            target_req = '%s==%s' % (loc_dist.name, loc_dist.version)
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
                target_req
            ])
            for item in os.listdir(tmp_dir):
                shutil.move(op.join(tmp_dir, item), op.join(target_dir, item))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        if res != 0:
            raise PundleException('%s was not installed due error' % (self.egg or loc_dist.name))
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
        latest = self.requirement.locate(suite)
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
        for req in dist.requires(extras=self.requirement.extras):
            suite.adjust_with_req(CustomReq(str(req), source=self.requirement), install=install, upgrade=upgrade)

    def frozen_dump(self):
        if self.requirement.egg:
            return self.requirement.line
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
            raise PundleException('Distribution is not installed %s' % self.key)
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
    def __init__(self, parser, urls=None):
        self.states = {}
        self.parser = parser
        self.urls = urls or ['https://pypi.python.org/simple/']
        self.locators = []
        for url in self.urls:
            self.locators.append(
                locators.SimpleScrapingLocator(url, timeout=3.0)
            )
        self.locators.append(locators.JSONLocator())
        self.locator = locators.AggregatingLocator(*self.locators, scheme='legacy')

    def locate(self, *a, **kw):
        return self.locator.locate(*a, **kw)

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
            state.activate()



class Parser(object):
    def __init__(self, directory='Pundledir', requirements_file=None, frozen_file='frozen.txt', package=None):
        self.directory = directory
        self.requirements_file = requirements_file
        self.frozen_file = frozen_file
        self.package = package

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
        dists = [
            next(iter(
                pkg_resources.find_distributions(op.join(self.directory, item), True)
            ), None)
            for item in os.listdir(self.directory) if '-' in item
        ]
        dists.extend(
            VCSDist(op.join(self.directory, item))
            for item in os.listdir(self.directory) if '+' in item
        )
        dists = filter(None, dists)
        result = defaultdict(list)
        for dist in dists:
            result[dist.key].append(dist)
        return result

    def parse_frozen(self):
        frozen = [(parse_vcs_requirement(line) or line.split('==')) for line in parse_file(self.frozen_file)] if op.exists(self.frozen_file) else []
        frozen_versions = dict((name.lower(), version) for name, version in frozen)
        return frozen_versions

    def parse_requirements(self):
        if self.requirements_file:
            requirements = parse_file(self.requirements_file)
            return dict((req.key, req) for req in (CustomReq(line, 'requirements file') for line in requirements))
        else:
            pkg = next(pkg_resources.find_distributions(self.package), None)
            if pkg is None:
                raise PundleException('There is no requirements.txt nor setup.py')
            return dict((req.key, CustomReq(str(req), 'setup.py')) for req in pkg.requires())


# Utilities
def search_files_upward(start_path=None):
    "Search for requirements.txt upward"
    if not start_path:
        start_path = op.abspath(op.curdir)
    if op.exists(op.join(start_path, 'requirements.txt')) or op.exists(op.join(start_path, 'setup.py')):
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
    params = {
        'frozen_file': op.join(base_path, 'frozen.txt'),
        'directory': op.join(pundledir_base, py_version_path)
    }
    if op.exists(op.join(base_path, 'requirements.txt')):
        params['requirements_file'] = op.join(base_path, 'requirements.txt')
    elif op.exists(op.join(base_path, 'setup.py')):
        params['package'] = base_path
    else:
        return
    return params


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
    suite.need_freeze()
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
    if not parser_kw:
        raise PundleException('Can`t create parser parameters')
    suite = Parser(**parser_kw).create_suite()
    if suite.need_freeze():
        raise PundleException('%s file is outdated' % suite.parser.frozen_file)
    if suite.need_install():
        raise PundleException('Some dependencies not installed')
    suite.activate_all()
    return suite


FIXATE_TEMPLATE = """
# pundle user customization start
import pundle; pundle.activate()
# pundle user customization end
"""

def fixate():
    "puts activation code to usercostumize.py for user"
    print_message('Fixate')
    import site
    userdir = site.getusersitepackages()
    if not userdir:
        raise PundleException('Can`t fixate due user have not site package directory')
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
    suite = activate()
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
    sys.path.insert(0, '')
    sys.argv = [cmd] + args
    exc()


def run_console():
    "starts python console with activated pundle environment"
    import readline
    import rlcompleter
    import atexit
    import code
    suite = activate()

    history_path = os.path.expanduser("~/.python_history")
    def save_history(history_path=history_path):
        readline.write_history_file(history_path)
    if os.path.exists(history_path):
        readline.read_history_file(history_path)
    atexit.register(save_history)

    readline.set_completer(rlcompleter.Completer(globals()).complete)
    readline.parse_and_bind("tab: complete")
    glob = globals()
    glob['pundle_suite'] = suite
    code.InteractiveConsole(locals=glob).interact()


class CmdRegister:
    commands = {}
    ordered = []

    @classmethod
    def cmdline(cls, *cmd_aliases):
        def wrap(func):
            for alias in cmd_aliases:
                cls.commands[alias] = func
                cls.ordered.append(alias)
        return wrap

    @classmethod
    def help(cls):
        for alias in cls.ordered:
            if not alias:
                continue
            print("{:15s} {}".format(alias, cls.commands[alias].__doc__))

    @classmethod
    def main(cls):
        alias = '' if len(sys.argv) == 1 else sys.argv[1]
        if alias == 'help':
            cls.help()
            return
        if not alias in cls.commands:
            print('Unknown command\nTry this:')
            cls.help()
            sys.exit(1)
        cls.commands[alias]()


@CmdRegister.cmdline('', 'install')
def cmd_install():
    "Install packages by frozen.txt and resolve ones that was not frozen"
    install_all(**create_parser_or_exit())


@CmdRegister.cmdline('upgrade')
def cmd_upgrade():
    "[package] if package provided will upgrade it and dependencies or all packages from PyPI"
    key = sys.argv[2] if len(sys.argv) > 2 else None
    upgrade_all(key=key, **create_parser_or_exit())


CmdRegister.cmdline('fixate')(fixate)


@CmdRegister.cmdline('exec')
def cmd_exec():
    "executes setuptools entry"
    execute(sys.argv[0], sys.argv[2], sys.argv[3:])


@CmdRegister.cmdline('entry_points')
def cmd_entry_points():
    "prints available setuptools entries"
    for entry, package in entry_points().items():
        print('%s (%s)' % (entry, package))


@CmdRegister.cmdline('edit')
def cmd_edit():
    "prints directory path to package"
    parser_kw = create_parser_parameters()
    suite = Parser(**parser_kw).create_suite()
    if suite.need_freeze():
        raise PundleException('%s file is outdated' % suite.parser.frozen_file)
    print(suite.states[sys.argv[2]].frozen_dist().location)


@CmdRegister.cmdline('info')
def cmd_info():
    "prints info about Pundle state"
    parser_kw = create_parser_parameters()
    suite = Parser(**parser_kw).create_suite()
    if suite.need_freeze():
        print('frozen.txt is outdated')
    else:
        print('frozen.txt is up to date')
    for state in suite.required_states():
        print('Requirement "{}", frozen {}, {}'.format(state.key, state.frozen, state.requirement.line if state.requirement else 'None'))
        print('Installed versions:')
        for dist in state.installed:
            print('    ', repr(dist))
        if not state.installed:
            print('     None')


CmdRegister.cmdline('console')(run_console)


@CmdRegister.cmdline('run')
def cmd_run():
    "executes given script"
    activate()
    sys.path.insert(0, '')
    script = sys.argv[2]
    sys.argv = [sys.argv[2]] + sys.argv[3:]
    exec(open(script).read(), {'__file__': script, '__name__': '__main__'})


@CmdRegister.cmdline('module')
def cmd_module():
    "executes module like `python -m`"
    activate()
    import runpy
    sys.path.insert(0, '')
    module = sys.argv[2]
    sys.argv = [sys.argv[2]] + sys.argv[3:]
    runpy.run_module(module, run_name='__main__')


@CmdRegister.cmdline('env')
def cmd_env():
    "populates PYTHONPATH with packages paths and executes command line in subprocess"
    activate()
    aug_env = os.environ.copy()
    aug_env['PYTHONPATH'] = ':'.join(sys.path)
    subprocess.call(sys.argv[2:], env=aug_env)


if __name__ == '__main__':
    # main()
    CmdRegister.main()