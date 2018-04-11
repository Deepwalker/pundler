import pundle


def test_pypy_python_version(mocker):
    sys_mock = mocker.patch('pundle.sys')
    platform_mock = mocker.patch('pundle.platform')
    platform_mock.python_implementation.return_value = 'PyPy'
    platform_mock.python_build.return_value = ('build1', 'blabla')
    class VersionInfo:
        major = 1
        minor = 2
        micro = 3
    sys_mock.pypy_version_info = VersionInfo
    assert pundle.python_version_string() == 'PyPy-1.2.3-build1'


def test_cpython_python_version(mocker):
    sys_mock = mocker.patch('pundle.sys')
    platform_mock = mocker.patch('pundle.platform')
    platform_mock.python_implementation.return_value = 'CPython'
    platform_mock.python_build.return_value = ('build1', 'blabla')
    class VersionInfo:
        major = 1
        minor = 2
        micro = 3
    sys_mock.version_info = VersionInfo
    assert pundle.python_version_string() == 'CPython-1.2.3-build1'
