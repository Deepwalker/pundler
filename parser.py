import os.path as op
import os
import functools
import shlex
import pkg_resources
cache_it = functools.lru_cache(None)


def parse_file(filename):
    return [req[0] for req in 
        filter(None, [shlex.split(line)
            for line in open(filename) if line.strip() and not line.startswith('#')
        ])
    ]


def test_vcs(req):
    return '+' in req and req.index('+') == 3

class FileSource(object):
    def __init__(self, filename):
        self.filename = filename

    def __repr__(self):
        return '<FileSource %r>' % self.filename

class CustomReq(object):
    def __init__(self, line, source=None):
        self.line = line
        self.req = pkg_resources.Requirement.parse(line)
        self.source = source

    def __contains__(self, something):
        return something in self.req

    def __repr__(self):
        return '<CustomReq %r>' % self.__dict__

    @property
    def key(self):
        return self.req.key


class Parser(object):
    def __init__(self, directory='Pundledir', requirements_file='requirements.txt', freezed_file='freezed.txt'):
        self.directory = directory
        self.requirements_file = requirements_file
        self.freezed_file = freezed_file

    def parse_directory(self):
        dir_items = [item.split('-', 1) for item in os.listdir(self.directory) if '-' in item]
        return dict((name.lower(), version) for name, version in dir_items)

    def parse_freezed(self):
        freezed = [line.split('==') for line in parse_file(self.freezed_file)] if op.exists(self.freezed_file) else []
        freezed_versions = dict((name.lower(), version) for name, version in freezed)
        return freezed_versions

    def correct_freezed(self):
        _, fit = self.get_not_installed(self.parse_requirements(), self.parse_freezed())
        return fit

    def freezed_for_check(self):
        return self.parse_file_requirements(self.freezed_file)

    def parse_requirements(self):
        return self.parse_file_requirements(self.requirements_file)

    @cache_it
    def parse_file_requirements(self, filename):
        requirements = parse_file(filename) if op.exists(filename) else []
        result = []
        for req in requirements:
            if test_vcs(req):
                print('Dont know how to work with vcs urls %r in `%s`' % (req, filename))
                continue
            result.append(CustomReq(req, source=FileSource(filename)))
        return result

    def get_not_installed(self, requirements, freezed_versions):
        nonfit = []
        fit = []
        for requirement in requirements:
            installed = freezed_versions.get(requirement.key)
            if not (installed and installed in requirement):
                nonfit.append(requirement)
            else:
                fit.append(requirement)
        return (nonfit, fit)

    def get_unresolved_requirements(self):
        are_freezed_correct, _ = self.get_not_installed(self.parse_requirements(), self.parse_freezed())
        are_freezed_installed, _ = self.get_not_installed(self.freezed_for_check(), self.parse_directory())
        return (are_freezed_correct, are_freezed_installed)


if __name__ == '__main__':
    parser = Parser()
    # Check if freezed fit with requirements
    are_freezed_correct, freezed_installed = parser.get_unresolved_requirements()
    print('Not freezed requirements', are_freezed_correct)
    # Check if freezed packages is installed
    print('Not installed freezed', freezed_installed)
