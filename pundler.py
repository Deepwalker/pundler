from __future__ import print_function, unicode_literals
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

# TODO bundle own version of distlib
from pip._vendor.distlib.locators import locate


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
        if isinstance(self.source, (str, unicode)):
            return '{} from {}'.format(self.line, self.source)
        if isinstance(self.source, CustomReq):
            return '{} from `{}`'.format(self.line, self.source.why_str())
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

    def locate_and_install(self, suite):
        loc_dist = locate(str(self.req))
        if not loc_dist:
            loc_dist = locate(str(self.req), prereleases=True)
        target_dir = op.join(suite.parser.directory, '{}-{}'.format(loc_dist.key, loc_dist.version))
        try:
            makedirs(target_dir)
        except FileExistsError:
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
    def __init__(self, key, req=None, freezed=None, installed=None):
        self.key = key
        self.requirement = req
        self.freezed = freezed
        self.installed = installed or []

    def __repr__(self):
        return '<RequirementState %r>' % self.__dict__

    def adjust_with_req(self, req):
        if self.requirement:
            self.requirement.adjust_with_req(req)
        else:
            self.requirement = req

    def has_correct_freeze(self):
        # print_message(self.key, self.requirement and self.freezed and self.freezed in self.requirement)
        return self.requirement and self.freezed and self.freezed in self.requirement

    def check_installed_version(self, suite, install=False):
        # install version of package if not installed
        dist = next(
            (installation for installation in self.installed if installation.version in self.requirement),
            None
        )
        if install and not dist:
            dist = self.requirement.locate_and_install(suite)
            self.installed.append(dist)
        if install and not self.has_correct_freeze():
            self.freezed = dist.version
        # if not dist:
            # raise Exception('Cannot install %r' % self.requirement)
        return dist

    def reveal_requirements(self, suite, install=False):
        dist = self.check_installed_version(suite, install=install)
        if not dist:
            return
        for req in dist.requires():
            suite.adjust_with_req(CustomReq(str(req), source=self.requirement), install=install)

    def freezed_dump(self):
        main = '{}=={}'.format(self.key, self.freezed)
        comment = self.requirement.why_str()
        return '{:20s} # {}'.format(main, comment)

    def freezed_dist(self):
        return next(
            ((dist if dist.version == self.freezed else None) for dist in self.installed),
            None
        )

    def install_freezed(self, suite):
        if self.freezed_dist() or not self.freezed:
            return
        freezed_req = CustomReq("{}=={}".format(self.key, self.freezed))
        dist = freezed_req.locate_and_install(suite)
        self.installed.append(dist)

    def activate(self):
        self.freezed_dist().activate()


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

    def need_refreeze(self):
        self.refreeze(install=False)
        not_correct = not all(state.has_correct_freeze() for state in self.required_states())
        # unneeded = any(state.freezed for state in self.states.values() if not state.requirement)
        return not_correct #or unneeded TODO

    def adjust_with_req(self, req, install=False):
        state = self.states.get(req.key)
        if not state:
            state = RequirementState(req.key, req=req)
            self.add(req.key, state)
        else:
            state.adjust_with_req(req)
        state.reveal_requirements(self, install=install)

    def refreeze(self, install=True):
        for state in self.required_states():
            state.reveal_requirements(self, install=install)

    def dump_freezed(self):
        return '\n'.join(sorted(
            state.freezed_dump() for state in self.required_states() if state.requirement
        )) + '\n'

    def need_install(self):
        return not all(state.freezed_dist() for state in self.states.values() if state.freezed)

    def install_freezed(self):
        for state in self.states.values():
            state.install_freezed(self)

    def activate_all(self):
        for state in self.required_states():
            state.activate()



class Parser(object):
    def __init__(self, directory='Pundledir', requirements_file='requirements.txt', freezed_file='freezed.txt'):
        self.directory = directory
        self.requirements_file = requirements_file
        self.freezed_file = freezed_file

    def create_suite(self):
        reqs, freezy, diry = self.parse_requirements(), self.parse_freezed(), self.parse_directory()
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

    def parse_freezed(self):
        freezed = [line.split('==') for line in parse_file(self.freezed_file)] if op.exists(self.freezed_file) else []
        freezed_versions = dict((name.lower(), version) for name, version in freezed)
        return freezed_versions

    def parse_requirements(self):
        requirements = parse_file(self.requirements_file) if op.exists(self.requirements_file) else []
        return dict((req.key, req) for req in (CustomReq(line, 'requirements file') for line in requirements))


# Commands
def freeze_them_all(*a, **kw):
    suite = Parser(*a, **kw).create_suite()
    if suite.need_refreeze():
        print_message('Freezed version is outdated')
        suite.refreeze()
        with open(suite.parser.freezed_file, 'w') as f:
            f.write(suite.dump_freezed())
        print_message(suite.dump_freezed())
    else:
        print_message('All up to date')


def check_if_freezed_installed(*a, **kw):
    suite = Parser(*a, **kw).create_suite()
    if suite.need_refreeze():
        print_message('Freezed version is outdated')
        sys.exit(1)
    if suite.need_install():
        print_message('Install some packages')
        suite.install_freezed()
    else:
        print_message('Nothing to do, all packages installed')
    return suite


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
    # print_message(base_path)
    if not base_path:
        return None
    py_version_path = python_version_string()
    return {
        'requirements_file': op.join(base_path, 'requirements.txt'),
        'freezed_file': op.join(base_path, 'freezed.txt'),
        'directory': op.join(op.expanduser('~'), '.pundledir', py_version_path)
    }


def create_parser_or_exit():
    parser_kw = create_parser_parameters()
    if not parser_kw:
        print_message('You have not requirements.txt. Create it and run again.')
        exit(1)
    return parser_kw

if __name__ == '__main__':
    # I think better have pundledir in special home user directory
    if len(sys.argv) == 1 or sys.argv[1] == 'install':
        check_if_freezed_installed(**create_parser_or_exit())

    elif sys.argv[1] == 'upgrade':
        freeze_them_all(**create_parser_or_exit())

    elif sys.argv[1] == 'fixate':
        print_message('Fixate')
        import site
        userdir = site.getusersitepackages()
        if not userdir:
            raise Exception('Can`t fixate due user have not site package directory')
        try:
            makedirs(userdir)
        except OSError:
            pass
        template = open(op.join(op.dirname(__file__), 'usercustomize.py')).read()
        template = template.replace('op.dirname(__file__)', "'%s'" % op.abspath(op.dirname(__file__)))
        usercustomize_file = op.join(userdir, 'usercustomize.py')
        print_message('Will edit %s file' % usercustomize_file)
        if op.exists(usercustomize_file):
            content = open(usercustomize_file).read()
            if '# pundler user costumization start' in content:
                regex = re.compile(r'\n# pundler user costumization start.*# pundler user costumization end\n', re.DOTALL)
                content, res = regex.subn(template, content)
                open(usercustomize_file, 'w').write(content)
            else:
                open(usercustomize_file, 'a').write(content)
        else:
            open(usercustomize_file, 'w').write(template)
        link_file = op.join(userdir, 'pundler.py')
        if op.lexists(link_file):
            print_message('Remove exist link to pundler')
            os.unlink(link_file)
        print_message('Create link to pundler %s' % link_file)
        os.symlink(op.abspath(__file__), link_file)
        print_message('Complete')

    elif sys.argv[1] == 'exec':
        # TODO proof implementation
        # clean it
        params = create_parser_or_exit()
        suite = check_if_freezed_installed(**params)
        entries = {}
        for r in suite.states.values():
            d = r.installed[0]
            scripts = d.get_entry_map().get('console_scripts', {})
            for name in scripts:
                entries[name] = d
        cmd = sys.argv[2]
        exc = entries[cmd].get_entry_info('console_scripts', cmd).load(require=False)
        old_arv = sys.argv
        sys.argv = [sys.argv[0]] + sys.argv[3:]
        exc()
        pass
