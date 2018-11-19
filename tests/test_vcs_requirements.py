from pundle import parse_vcs_requirement


def test_parse_vcs_requirement():
    assert parse_vcs_requirement('git+https://github.com/pampam/PKG.git@master#egg=PKG') == \
        ('pkg', 'git+https://github.com/pampam/PKG.git@master#egg=PKG', None)
