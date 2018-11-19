from __future__ import print_function
import re
try:
    from urllib.parse import urlparse, parse_qsl
except ImportError:  # pragma: no cover
    from urlparse import urlparse, parse_qsl
from collections import defaultdict
from base64 import b64encode, b64decode
import platform
import os.path as op
import os
from os import makedirs
import stat
import tempfile
import shutil
import subprocess
import sys
import shlex
import json
import hashlib
import pkg_resources
try:
    from pip import main as pip_exec
except ImportError:
    from pip._internal import main as pip_exec

# TODO bundle own version of distlib. Perhaps
try:
    from pip._vendor.distlib import locators
except ImportError:  # pragma: no cover
    from pip.vendor.distlib import locators

try:
    str_types = (basestring,)
except NameError:  # pragma: no cover
    str_types = (str, bytes)

try:
    pkg_resources_parse_version = pkg_resources.SetuptoolsVersion
except AttributeError:  # pragma: no cover
    pkg_resources_parse_version = pkg_resources.packaging.version.Version


def print_message(*a, **kw):
    print(*a, **kw)


class PundleException(Exception):
    pass


def python_version_string():
    if platform.python_implementation() == 'PyPy':
        version_info = sys.pypy_version_info
    else:
        version_info = sys.version_info
    version_string = '{v.major}.{v.minor}.{v.micro}'.format(v=version_info)
    build, _ = platform.python_build()
    build = build.replace(':', '_')  # windows do not understand `:` in path
    return '{}-{}-{}'.format(platform.python_implementation(), version_string, build)


def parse_file(filename):
    res = []
    with open(filename) as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith('#'):
                if s.startswith('-r'):
                    continue
                if s.startswith('-e '):
                    s = s[3:].strip()
                if parse_vcs_requirement(s):
                    res.append(s)
                else:
                    req = shlex.split(s, comments=True)
                    res.append(req[0])
    return res


def test_vcs(req):
    return '+' in req and req.index('+') == 3


def parse_vcs_requirement(req):
    if '+' not in req:
        return None
    vcs, url = req.split('+', 1)
    if vcs not in ('git', 'svn', 'hg'):
        return None
    parsed_url = urlparse(url)
    parsed = dict(parse_qsl(parsed_url.fragment))
    if 'egg' not in parsed:
        return None
    egg = parsed['egg'].rsplit('-', 1)
    if len(egg) > 1:
        try:
            pkg_resources_parse_version(egg[1])
        except pkg_resources._vendor.packaging.version.InvalidVersion:
            return parsed['egg'].lower(), req, None
        return egg[0].lower(), req, egg[1]
    else:
        return parsed['egg'].lower(), req, None


def parse_frozen_vcs(req):
    res = parse_vcs_requirement(req)
    if not res:
        return
    return res[0], res[1]


class VCSDist(object):
    def __init__(self, directory):
        self.dir = directory
        name = op.split(directory)[-1]
        key, encoded = name.split('+', 1)
        self.key = key.lower()
        self.line = b64decode(encoded).decode('utf-8')
        egg, req, version = parse_vcs_requirement(self.line)
        version = version or '0.0.0'
        self.hashcmp = (pkg_resources_parse_version(version), -1, egg, self.dir)
        self.version = self.line
        self.pkg_resource = next(iter(pkg_resources.find_distributions(self.dir, True)), None)
        self.location = self.pkg_resource.location

    def requires(self, extras=[]):
        return self.pkg_resource.requires(extras=extras)

    def activate(self):
        return self.pkg_resource.activate()

    def __lt__(self, other):
        return self.hashcmp.__lt__(other.hashcmp)


class CustomReq(object):
    def __init__(self, line, env, source=None):
        self.line = line
        self.egg = None
        if isinstance(line, pkg_resources.Requirement):
            self.req = line
        elif test_vcs(line):
            res = parse_vcs_requirement(line)
            if not res:
                raise PundleException('Bad url %r' % line)
            egg, req, version = res
            self.egg = egg
            self.req = None  # pkg_resources.Requirement.parse(res)
        else:
            self.req = pkg_resources.Requirement.parse(line)
        self.sources = set([source])
        self.envs = set()
        self.add_env(env)

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
        if len(self.sources) < 2:
            return '{} << {}'.format(self.line, self.why_str_one(list(self.sources)[0]))
        causes = list(sorted(self.why_str_one(source) for source in self.sources))
        return '{} << [{}]'.format(self.line, ' | '.join(causes))

    def why_str_one(self, source):
        if isinstance(source, str_types):
            return source
        elif isinstance(source, CustomReq):
            return source.why_str()
        return '?'

    def adjust_with_req(self, req):
        if not self.req:
            return
            raise PundleException('VCS')
        versions = ','.join(''.join(t) for t in set(self.req.specs + req.req.specs))
        self.requirement = pkg_resources.Requirement.parse('{} {}'.format(
            self.req.project_name, versions
        ))
        self.sources.update(req.sources)
        self.add_env(req.envs)

    @property
    def key(self):
        return self.req.key if self.req else self.egg

    @property
    def extras(self):
        return self.req.extras if self.req else []

    def locate(self, suite, prereleases=False):
        # requirements can have somethin after `;` symbol that `locate` does not understand
        req = str(self.req).split(';', 1)[0]
        dist = suite.locate(req, prereleases=prereleases)
        if not dist:
            # have not find any releases so search for pre
            dist = suite.locate(req, prereleases=True)
        if not dist:
            raise PundleException('%s can not be located' % self.req)
        return dist

    def locate_and_install(self, suite, installed=None, prereleases=False):
        if self.egg:
            key = b64encode(self.line.encode('utf-8')).decode()
            target_dir = op.join(suite.parser.directory, '{}+{}'.format(self.egg, key))
            target_req = self.line
            ready = [
                installation
                for installation in (installed or [])
                if getattr(installation, 'line', None) == self.line
            ]
        else:
            loc_dist = self.locate(suite, prereleases=prereleases)
            ready = [
                installation
                for installation in (installed or [])
                if installation.version == loc_dist.version
            ]
            target_dir = op.join(suite.parser.directory, '{}-{}'.format(loc_dist.key, loc_dist.version))
            # DEL? target_req = '%s==%s' % (loc_dist.name, loc_dist.version)
            # If we use custom index, then we want not to configure PIP with it
            # and just give it URL
            target_req = loc_dist.download_url
        if ready:
            return ready[0]
        try:
            makedirs(target_dir)
        except OSError:
            pass
        tmp_dir = tempfile.mkdtemp()
        print('Use temp dir', tmp_dir)
        try:
            print('pip install --no-deps -t %s %s' % (tmp_dir, target_req))
            pip_exec([
                'install',
                '--no-deps',
                '-t', tmp_dir,
                '-v',
                target_req
            ])
            for item in os.listdir(tmp_dir):
                shutil.move(op.join(tmp_dir, item), op.join(target_dir, item))
        except Exception as exc:
            raise PundleException('%s was not installed due error %s' % (self.egg or loc_dist.name, exc))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return next(iter(pkg_resources.find_distributions(target_dir, True)), None)

    def add_env(self, env):
        if isinstance(env, str):
            self.envs.add(env)
        else:
            self.envs.update(env)


class RequirementState(object):
    """Holds requirement state, like what version do we have installed, is
    some version frozen or not, what requirement constrains do we have.
    """
    def __init__(self, key, req=None, frozen=None, installed=None, hashes=None):
        self.key = key
        self.requirement = req
        self.frozen = frozen
        self.hashes = hashes
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
            dist = [
                installation
                for installation in self.installed
                if pkg_resources.parse_version(installation.version) == pkg_resources.parse_version(self.frozen)
            ]
            dist = dist[0] if dist else None
            if install and not dist:
                dist = self.install_frozen(suite)
        if install and not dist:
            dist = self.requirement.locate_and_install(suite, installed=self.get_installed())
            if dist is None:
                print('Package %s was not installed due some error' % self.key)
                raise PundleException('Package %s was not installed due some error' % self.key)
            self.frozen = dist.version
            self.installed.append(dist)
            self.frozen = dist.version
        return dist

    def get_installed(self):
        return [installation for installation in self.installed if installation.version in self.requirement]

    def upgrade(self, suite, prereleases=False):
        # check if we have fresh packages on PIPY
        dists = self.get_installed()
        dist = dists[0] if dists else None
        latest = self.requirement.locate(suite, prereleases=prereleases)
        if not dist or pkg_resources.parse_version(latest.version) > pkg_resources.parse_version(dist.version):
            print_message('Upgrade to', latest)
            dist = self.requirement.locate_and_install(suite, installed=self.get_installed(), prereleases=prereleases)
        # Anyway use latest available dist
        self.frozen = dist.version
        self.installed.append(dist)
        return dist

    def reveal_requirements(self, suite, install=False, upgrade=False, already_revealed=None, prereleases=False):
        already_revealed = already_revealed.copy() if already_revealed is not None else set()
        if self.key in already_revealed:
            return
        if upgrade:
            dist = self.upgrade(suite, prereleases=prereleases)
        else:
            dist = self.check_installed_version(suite, install=install)
        if not dist:
            return
        already_revealed.add(self.key)
        for req in dist.requires(extras=self.requirement.extras):
            suite.adjust_with_req(
                CustomReq(str(req), self.requirement.envs, source=self.requirement),
                install=install,
                upgrade=upgrade,
                already_revealed=already_revealed,
            )

    def frozen_dump(self):
        if self.requirement.egg:
            return self.requirement.line
        main = '{}=={}'.format(self.key, self.frozen)
        comment = self.requirement.why_str()
        return '{:20s} # {}'.format(main, comment)

    def frozen_dist(self):
        if not self.frozen:
            return
        for dist in self.installed:
            if pkg_resources.parse_version(dist.version) == pkg_resources.parse_version(self.frozen):
                return dist

    def install_frozen(self, suite):
        if self.frozen_dist() or not self.frozen:
            return
        envs = self.requirement.envs if self.requirement else ''
        if test_vcs(self.frozen):
            frozen_req = CustomReq(self.frozen, envs)
        else:
            frozen_req = CustomReq("{}=={}".format(self.key, self.frozen), envs)
        dist = frozen_req.locate_and_install(suite)
        self.installed.append(dist)
        return dist

    def activate(self):
        dist = self.frozen_dist()
        if not dist:
            raise PundleException('Distribution is not installed %s' % self.key)
        dist.activate()
        pkg_resources.working_set.add_entry(dist.location)
        # find end execute *.pth
        sitedir = dist.location  # noqa some PTH search for sitedir
        for filename in os.listdir(dist.location):
            if not filename.endswith('.pth'):
                continue
            try:
                for line in open(op.join(dist.location, filename)):
                    if line.startswith('import '):
                        exec(line.strip())
            except Exception as e:
                print('Erroneous pth file %r' % op.join(dist.location, filename))
                print(e)


class AggregatingLocator(object):
    def __init__(self, locators):
        self.locators = locators

    def locate(self, req, **kw):
        for locator in self.locators:
            print_message('try', locator, 'for', req)
            revealed = locator.locate(req, **kw)
            if revealed:
                return revealed


class Suite(object):
    """
    Main object that represents current directory pundle state
    """
    def __init__(self, parser, envs=[], urls=None):
        self.states = {}
        self.parser = parser
        self.envs = envs
        self.urls = urls or ['https://pypi.python.org/simple/']
        if 'PIP_EXTRA_INDEX_URL' in os.environ:
            self.urls.append(os.environ['PIP_EXTRA_INDEX_URL'])
        self.locators = []
        for url in self.urls:
            self.locators.append(
                locators.SimpleScrapingLocator(url, timeout=3.0, scheme='legacy')
            )
        self.locators.append(locators.JSONLocator(scheme='legacy'))
        self.locator = AggregatingLocator(self.locators)

    def use(self, key):
        """For single mode
        You can call suite.use('arrow') and then `import arrow`

        :key: package name
        """
        self.adjust_with_req(CustomReq(key, ''))
        self.install()
        self.activate_all()

    def locate(self, *a, **kw):
        return self.locator.locate(*a, **kw)

    def add(self, key, state):
        self.states[key] = state

    def __repr__(self):
        return '<Suite %r>' % self.states

    def required_states(self):
        return [state for state in self.states.values() if state.requirement]

    def need_freeze(self, verbose=False):
        self.install(install=False)
        not_correct = not all(state.has_correct_freeze() for state in self.required_states())
        if not_correct and verbose:
            for state in self.required_states():
                if not state.has_correct_freeze():
                    print(
                        state.key,
                        'Need',
                        state.requirement,
                        'have not been frozen',
                        state.frozen,
                        ', installed',
                        state.installed
                    )
        # TODO
        # unneeded = any(state.frozen for state in self.states.values() if not state.requirement)
        # if unneeded:
        #     print('!!! Unneeded', [state.key for state in self.states.values() if not state.requirement])
        return not_correct  # or unneeded

    def adjust_with_req(self, req, install=False, upgrade=False, already_revealed=None):
        state = self.states.get(req.key)
        if not state:
            state = RequirementState(req.key, req=req)
            self.add(req.key, state)
        else:
            state.adjust_with_req(req)
        state.reveal_requirements(self, install=install, upgrade=upgrade, already_revealed=already_revealed or set())

    def install(self, install=True):
        for state in self.required_states():
            state.reveal_requirements(self, install=install)

    def upgrade(self, key=None, prereleases=False):
        states = [self.states[key]] if key else self.required_states()
        for state in states:
            print('Check', state.requirement.req)
            state.reveal_requirements(self, upgrade=True, prereleases=prereleases)

    def get_frozen_states(self, env):
        return [
            state
            for state in self.required_states()
            if state.requirement and env in state.requirement.envs
        ]

    def need_install(self):
        return not all(state.frozen_dist() for state in self.states.values() if state.frozen)

    def install_frozen(self):
        for state in self.states.values():
            state.install_frozen(self)

    def activate_all(self, envs=('',)):
        for state in self.required_states():
            if '' in state.requirement.envs or any(env in state.requirement.envs for env in envs):
                state.activate()

    def save_frozen(self):
        "Saves frozen files to disk"
        states_by_env = dict(
            (env, self.get_frozen_states(env))
            for env in self.parser.envs()
        )
        self.parser.save_frozen(states_by_env)


class Parser(object):
    """Gather environment info, requirements,
    frozen packages and create Suite object
    """
    def __init__(
            self,
            base_path=None,
            directory='Pundledir',
            requirements_files=None,
            frozen_files=None,
            package=None,
    ):
        self.base_path = base_path or '.'
        self.directory = directory
        self.requirements_files = requirements_files
        if frozen_files is None:
            self.frozen_files = {'': 'frozen.txt'}
        else:
            self.frozen_files = frozen_files
        self.package = package
        self.package_envs = set([''])

    def envs(self):
        if self.requirements_files:
            return list(self.requirements_files.keys()) or ['']
        elif self.package:
            return self.package_envs
        return ['']

    def get_frozen_file(self, env):
        if env in self.frozen_files:
            return self.frozen_files[env]
        else:
            return os.path.join(self.base_path, 'frozen_%s.txt' % env)

    def create_suite(self):
        reqs = self.parse_requirements()
        freezy = self.parse_frozen()
        hashes = self.parse_frozen_hashes()
        diry = self.parse_directory()
        state_keys = set(list(reqs.keys()) + list(freezy.keys()) + list(diry.keys()))
        suite = Suite(self, envs=self.envs())
        for key in state_keys:
            suite.add(
                key,
                RequirementState(
                    key,
                    req=reqs.get(key),
                    frozen=freezy.get(key),
                    installed=diry.get(key, []),
                    hashes=hashes.get(key),
                ),
            )
        return suite

    def parse_directory(self):
        if not op.exists(self.directory):
            return {}
        dists = [
            # this magic takes first element or None
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
        frozen_versions = {}
        for env in self.envs():
            frozen_file = self.get_frozen_file(env)
            if op.exists(frozen_file):
                frozen = [
                    (parse_frozen_vcs(line) or line.split('=='))
                    for line in parse_file(frozen_file)
                ]
            else:
                frozen = []
            for name, version in frozen:
                frozen_versions[name.lower()] = version
        return frozen_versions

    def parse_frozen_hashes(self):
        """This implementation does not support hashes yet
        """
        return {}

    def parse_requirements(self):
        all_requirements = {}
        for env, req_file in self.requirements_files.items():
            requirements = parse_file(req_file)
            if env:
                source = 'requirements %s file' % env
            else:
                source = 'requirements file'
            for line in requirements:
                req = CustomReq(line, env, source=source)
                if req.key in all_requirements:
                    # if requirements exists in other env, then add this env too
                    all_requirements[req.key].add_env(env)
                else:
                    all_requirements[req.key] = req
        return all_requirements

    def save_frozen(self, states_by_env):
        for env, states in states_by_env.items():
            data = '\n'.join(sorted(
                state.frozen_dump()
                for state in states
            )) + '\n'
            frozen_file = self.get_frozen_file(env)
            with open(frozen_file, 'w') as f:
                f.write(data)


class SingleParser(Parser):
    def parse_requirements(self):
        return {}


class SetupParser(Parser):
    def parse_requirements(self):
        setup_info = get_info_from_setup(self.package)
        if setup_info is None:
            raise PundleException('There is no requirements.txt nor setup.py')
        install_requires = setup_info.get('install_requires') or []
        reqs = [
            CustomReq(str(req), '', source='setup.py')
            for req in install_requires
        ]
        requirements = dict((req.key, req) for req in reqs)
        # we use `feature` as environment for pundle
        extras_require = (setup_info.get('extras_require') or {})
        for feature, feature_requires in extras_require.items():
            for req_line in feature_requires:
                req = CustomReq(req_line, feature, source='setup.py')
                # if this req already in dict, then add our feature as env
                if req.key in requirements:
                    requirements[req.key].add_env(feature)
                else:
                    requirements[req.key] = req
            self.package_envs.add(feature)
        return requirements


class PipfileParser(Parser):
    DEFAULT_PIPFILE_SOURCES = [
        {
            'name': 'pypi',
            'url': 'https://pypi.python.org/simple',
            'verify_ssl': True,
        },
    ]

    def __init__(self, **kw):
        self.pipfile = kw.pop('pipfile')
        self.pipfile_envs = set([''])
        super(PipfileParser, self).__init__(**kw)
        # cache
        self.loaded_pipfile = None
        self.loaded_pipfile_lock = None

    def envs(self):
        return self.pipfile_envs

    def pipfile_content(self):
        import toml
        if self.loaded_pipfile:
            return self.loaded_pipfile
        self.loaded_pipfile = toml.load(open(self.pipfile))
        return self.loaded_pipfile

    def pipfile_lock_content(self):
        if self.loaded_pipfile_lock:
            return self.loaded_pipfile_lock
        try:
            self.loaded_pipfile_lock = json.load(open(self.pipfile + '.lock'))
        except Exception:
            pass
        return self.loaded_pipfile_lock

    def parse_requirements(self):
        info = self.pipfile_content()
        all_requirements = {}
        for info_key in info:
            if not info_key.endswith('packages'):
                continue
            if '-' in info_key:
                env, _ = info_key.split('-', 1)
            else:
                env = ''
            self.pipfile_envs.add(env)
            for key, details in info[info_key].items():
                if isinstance(details, str_types):
                    if details != '*':
                        key = key + details  # details is a version requirement
                    req = CustomReq(key, env, source='Pipfile')
                else:
                    # a dict
                    if 'file' in details or 'path' in details:
                        raise PundleException('Unsupported Pipfile feature yet %s: %r' % (key, details))
                    if 'git' in details:
                        # wow, this as a git package!
                        req = CustomReq('git+%s#egg=%s' % (details['git'], key), env, source='Pipfile')
                    else:
                        # else just simple requirement
                        req = CustomReq(key + details['version'], env, source='Pipfile')
                if req.key in all_requirements:
                    # if requirements exists in other env, then add this env too
                    all_requirements[req.key].add_env(env)
                else:
                    all_requirements[req.key] = req
        return all_requirements

    def parse_frozen(self):
        parsed_frozen = self.pipfile_lock_content()
        if parsed_frozen is None:
            return {}
        frozen_versions = {}
        for env in parsed_frozen:
            if env.startswith('_'):
                # this is not an env
                continue
            for key, details in parsed_frozen[env].items():
                if 'vcs' in details:
                    frozen_versions[key] = details['vcs']
                else:
                    frozen_versions[key] = details.get('version', '0.0.0').lstrip('=')
        return frozen_versions

    def parse_frozen_hashes(self):
        parsed_frozen = self.pipfile_lock_content()
        if parsed_frozen is None:
            return {}
        frozen_versions = {}
        for env in parsed_frozen:
            if env.startswith('_'):
                # this is not an env
                continue
            for key, details in parsed_frozen[env].items():
                frozen_versions[key] = details.get('hashes', [])
        return frozen_versions

    def hash(self):
        """Returns the SHA256 of the pipfile's data.
        From pipfile.
        """
        pipfile_content = self.pipfile_content()
        data = {
            '_meta': {
                'sources': pipfile_content.get('sources') or self.DEFAULT_PIPFILE_SOURCES,
                'requires': pipfile_content.get('requires') or {},
            },
            'default': pipfile_content.get('packages') or {},
            'develop': pipfile_content.get('dev-packages') or {},
        }
        content = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode("utf8")).hexdigest()

    def save_frozen(self, states_by_env):
        """Implementation is not complete.
        """
        data = self.pipfile_lock_content() or {}
        data.setdefault('_meta', {
            'pipfile-spec': 5,
            'requires': {},
            'sources': self.DEFAULT_PIPFILE_SOURCES,
        })
        data.setdefault('_meta', {}).setdefault('hash', {})['sha256'] = self.hash()
        for env, states in states_by_env.items():
            if env == '':
                env_key = 'default'
            elif env == 'dev':
                env_key = 'develop'
            else:
                env_key = env
            reqs = data.setdefault(env_key, {})
            for state in states:
                if state.requirement.egg:
                    egg, url, version = parse_vcs_requirement(state.requirement.line)
                    reqs[state.key] = {
                        'vcs': url,
                    }
                else:
                    reqs[state.key] = {
                        'version': '==' + state.frozen,
                        'hashes': state.hashes or [],
                    }
        with open(self.pipfile + '.lock', 'w') as f:
            f.write(json.dumps(data, sort_keys=True, indent=4))


def create_parser(**parser_args):
    if parser_args.get('requirements_files'):
        return Parser(**parser_args)
    elif parser_args.get('package'):
        return SetupParser(**parser_args)
    elif parser_args.get('pipfile'):
        return PipfileParser(**parser_args)
    return SingleParser(**parser_args)


# Utilities
def get_info_from_setup(path):
    """Mock setuptools.setup(**kargs) to get
    package information about requirements and extras
    """
    preserve = {}

    def _save_info(**setup_args):
        preserve['args'] = setup_args

    import setuptools
    original_setup = setuptools.setup
    setuptools.setup = _save_info
    import runpy
    runpy.run_path(os.path.join(path, 'setup.py'), run_name='__main__')
    setuptools.setup = original_setup
    return preserve.get('args')


def search_files_upward(start_path=None):
    "Search for requirements.txt upward"
    if not start_path:
        start_path = op.abspath(op.curdir)
    if any(
            op.exists(op.join(start_path, filename))
            for filename in ('requirements.txt', 'setup.py', 'Pipfile')
    ):
        return start_path
    up_path = op.abspath(op.join(start_path, '..'))
    if op.samefile(start_path, up_path):
        return None
    return search_files_upward(start_path=up_path)


def find_all_prefixed_files(directory, prefix):
    "find all requirements_*.txt files"
    envs = {}
    for entry in os.listdir(directory):
        if not entry.startswith(prefix):
            continue
        name, ext = op.splitext(entry)
        env = name[len(prefix):].lstrip('_')
        envs[env] = op.join(directory, entry)
    return envs


def create_parser_parameters():
    base_path = search_files_upward()
    if not base_path:
        raise PundleException('Can not find requirements.txt nor setup.py nor Pipfile')
    py_version_path = python_version_string()
    pundledir_base = os.environ.get('PUNDLEDIR') or op.join(op.expanduser('~'), '.pundledir')
    if op.exists(op.join(base_path, 'requirements.txt')):
        requirements_files = find_all_prefixed_files(base_path, 'requirements')
    else:
        requirements_files = {}
    envs = list(requirements_files.keys()) or ['']
    params = {
        'base_path': base_path,
        'frozen_files': {
            env: op.join(base_path, 'frozen_%s.txt' % env if env else 'frozen.txt')
            for env in envs
        },
        'directory': op.join(pundledir_base, py_version_path),
    }
    if requirements_files:
        params['requirements_files'] = requirements_files
    elif op.exists(op.join(base_path, 'setup.py')):
        params['package'] = base_path
    elif op.exists(op.join(base_path, 'Pipfile')):
        params['pipfile'] = op.join(base_path, 'Pipfile')
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
def upgrade_all(**kw):
    key = kw.pop('key')
    prereleases = kw.pop('prereleases')
    suite = create_parser(**kw).create_suite()
    suite.need_freeze()
    suite.upgrade(key=key, prereleases=prereleases)
    suite.install()
    suite.save_frozen()


def install_all(**kw):
    suite = create_parser(**kw).create_suite()
    if suite.need_freeze() or suite.need_install():
        print_message('Install some packages')
        suite.install()
    else:
        print_message('Nothing to do, all packages installed')
    suite.save_frozen()
    return suite


def activate():
    parser_kw = create_parser_parameters()
    if not parser_kw:
        raise PundleException('Can`t create parser parameters')
    suite = create_parser(**parser_kw).create_suite()
    if suite.need_freeze(verbose=True):
        raise PundleException('frozen file is outdated')
    if suite.need_install():
        raise PundleException('Some dependencies not installed')
    envs = (os.environ.get('PUNDLEENV') or '').split(',')
    suite.activate_all(envs=envs)
    return suite


FIXATE_TEMPLATE = """
# pundle user customization start
import pundle; pundle.activate()
# pundle user customization end
"""


def fixate():
    "puts activation code to usercustomize.py for user"
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
        if isinstance(d, VCSDist):
            continue
        scripts = d.get_entry_map().get('console_scripts', {})
        for name in scripts:
            entries[name] = d
    return entries


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
        if alias not in cls.commands:
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
    """
    [package [pre]] if package provided will upgrade it and dependencies or all packages from PyPI.
    If `pre` provided will look for prereleases.
    """
    key = sys.argv[2] if len(sys.argv) > 2 else None
    prereleases = sys.argv[3] == 'pre' if len(sys.argv) > 3 else False
    upgrade_all(key=key, prereleases=prereleases, **create_parser_or_exit())


CmdRegister.cmdline('fixate')(fixate)


@CmdRegister.cmdline('exec')
def cmd_exec():
    "executes setuptools entry"
    cmd = sys.argv[2]
    args = sys.argv[3:]
    entries = entry_points()
    if cmd not in entries:
        print_message('Script is not found. Check if package is installed, or look at the `pundle entry_points`')
        sys.exit(1)
    exc = entries[cmd].get_entry_info('console_scripts', cmd).load()
    sys.path.insert(0, '')
    sys.argv = [cmd] + args
    exc()


@CmdRegister.cmdline('entry_points')
def cmd_entry_points():
    "prints available setuptools entries"
    for entry, package in entry_points().items():
        print('%s (%s)' % (entry, package))


@CmdRegister.cmdline('edit')
def cmd_edit():
    "prints directory path to package"
    parser_kw = create_parser_parameters()
    suite = create_parser(**parser_kw).create_suite()
    if suite.need_freeze():
        raise PundleException('%s file is outdated' % suite.parser.frozen_file)
    print(suite.states[sys.argv[2]].frozen_dist().location)


@CmdRegister.cmdline('info')
def cmd_info():
    "prints info about Pundle state"
    parser_kw = create_parser_parameters()
    suite = create_parser(**parser_kw).create_suite()
    if suite.need_freeze():
        print('frozen.txt is outdated')
    else:
        print('frozen.txt is up to date')
    for state in suite.required_states():
        print(
            'Requirement "{}", frozen {}, {}'.format(
                state.key,
                state.frozen,
                state.requirement.line if state.requirement else 'None'
            )
        )
        print('Installed versions:')
        for dist in state.installed:
            print('    ', repr(dist))
        if not state.installed:
            print('     None')


def run_console(glob):
    import readline
    import rlcompleter
    import atexit
    import code

    history_path = os.path.expanduser("~/.python_history")

    def save_history(history_path=history_path):
        readline.write_history_file(history_path)
    if os.path.exists(history_path):
        readline.read_history_file(history_path)

    atexit.register(save_history)

    readline.set_completer(rlcompleter.Completer(glob).complete)
    readline.parse_and_bind("tab: complete")
    code.InteractiveConsole(locals=glob).interact()


@CmdRegister.cmdline('console')
def cmd_console():
    "[ipython|bpython|ptpython] starts python console with activated pundle environment"
    suite = activate()
    glob = {
        'pundle_suite': suite,
    }
    interpreter = sys.argv[2] if len(sys.argv) > 2 else None
    if not interpreter:
        run_console(glob)
    elif interpreter == 'ipython':
        from IPython import embed
        embed()
    elif interpreter == 'ptpython':
        from ptpython.repl import embed
        embed(glob, {})
    elif interpreter == 'bpython':
        from bpython import embed
        embed(glob)
    else:
        raise PundleException('Unknown interpreter: {}. Choose one of None, ipython, bpython, ptpython.')


@CmdRegister.cmdline('run')
def cmd_run():
    "executes given script"
    activate()
    import runpy
    sys.path.insert(0, '')
    script = sys.argv[2]
    sys.argv = [sys.argv[2]] + sys.argv[3:]
    runpy.run_path(script, run_name='__main__')


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


@CmdRegister.cmdline('print_env')
def cmd_print_env():
    "Prints PYTHONPATH. For usage with mypy and MYPYPATH"
    suite = activate()
    path = ':'.join(
        state.frozen_dist().location
        for state in suite.states.values()
        if state.frozen_dist()
    )
    print(path)


ENTRY_POINT_TEMPLATE = '''#! /usr/bin/env python
import pundle; pundle.activate()
pundle.entry_points()['{entry_point}'].get_entry_info('console_scripts', '{entry_point}').load(require=False)()
'''


@CmdRegister.cmdline('linkall')
def link_all():
    "links all packages to `.pundle_local` dir"
    local_dir = '.pundle_local'
    suite = activate()

    try:
        makedirs(local_dir)
    except OSError:
        pass
    local_dir_info = {de.name: de for de in os.scandir(local_dir)}
    for r in suite.states.values():
        d = r.frozen_dist()
        if not d:
            continue
        for dir_entry in os.scandir(d.location):
            if dir_entry.name.startswith('__') or dir_entry.name.startswith('.') or dir_entry.name == 'bin':
                continue
            dest_path = os.path.join(local_dir, dir_entry.name)
            if dir_entry.name in local_dir_info:
                sym = local_dir_info.pop(dir_entry.name)
                existed = op.realpath(sym.path)
                if existed == dir_entry.path:
                    continue
                os.remove(sym.path)
            os.symlink(dir_entry.path, dest_path)
    # create entry_points binaries
    try:
        makedirs(os.path.join(local_dir, 'bin'))
    except OSError:
        pass
    for bin_name, entry_point in entry_points().items():
        bin_filename = os.path.join(local_dir, 'bin', bin_name)
        open(bin_filename, 'w').write(ENTRY_POINT_TEMPLATE.format(entry_point=bin_name))
        file_stat = os.stat(bin_filename)
        os.chmod(bin_filename, file_stat.st_mode | stat.S_IEXEC)
    local_dir_info.pop('bin')

    # remove extra links
    for de in local_dir_info:
        os.remove(de.path)


@CmdRegister.cmdline('show_requirements')
def show_requirements():
    "shows details requirements info"
    suite = activate()
    for name, state in suite.states.items():
        if state.requirement:
            print(
                name,
                'frozen:',
                state.frozen,
                'required:',
                state.requirement.req if state.requirement.req else 'VCS',
                state.requirement.envs,
            )


# Single mode that you can use in console
_single_mode_suite = {}  # cache variable to keep current suite for single_mode


def single_mode():
    """ Create, cache and return Suite instance for single_mode.
    """
    if not _single_mode_suite:
        py_version_path = python_version_string()
        pundledir_base = os.environ.get('PUNDLEDIR') or op.join(op.expanduser('~'), '.pundledir')
        directory = op.join(pundledir_base, py_version_path)
        _single_mode_suite['cache'] = create_parser(directory=directory).create_suite()
    return _single_mode_suite['cache']


def use(key):
    """ Installs `key` requirement, like `django==1.11` or just `django`
    """
    suite = single_mode()
    suite.use(key)


if __name__ == '__main__':
    CmdRegister.main()
