Pundler
=======

Python bundler alike alternative to virtualenv for development. Plays best with pyenv.
For deployment use virtualenv or something special.

For now works only with PyPI packages.
Git, svn and others support planned.


Prerequisites
-------------

- I recommend using pyenv
- requires setuptools
- requires pip


Commands
--------

`pundler [install]` will install files from frozen.txt file and reveal
    new requirements if something is not frozen yet.

`pundler upgrade` will recreate frozen.txt from requirements.txt.

`pundler fixate` installs site customization for current python.

`pundler exec cmd [args]` executes entry point from one of the installed packages.

`pundler entry_points` prints entry points from all packages.

`pundler edit [package]` returns path to package directory.


How to play with it
-------------------

Simple with usercustomize.py:

    git clone git@github.com:Deepwalker/pundler.git
    python pundler/pundler.py fixate

    cd testproject
    python -m pundler upgrade

Pundler will create directory `~/.pundledir` and file `frozen.txt`.

Or you can make ``alias pundler='python /full/path/to/pundler/pundler.py'`` and use it.
And add ``/full/path/to/pundler`` to your ``PYTHONPATH``.
But you will need to manual load dependencies in your project start script, like this:

    import pundler
    parser_kw = pundler.create_parser_parameters()
    suite = pundler.Parser(**parser_kw).create_suite()
    if suite.need_freeze():
        raise Exception('%s file is outdated' % suite.parser.frozen_file)
    if suite.need_install():
        raise Exception('Some dependencies not installed')
    suite.activate_all()


DONE
----
- install according to frozen.txt
- on update rewrite frozen.txt
- on launch check if frozen.txt is in touch with requirements.txt
- search through hierarchy upward
- tie packages to python version.
- package scripts
- upgrade must lookup PyPI for new version
- in install mode if requirement is not frozen, then install latest package from PyPI. Else install frozen version.
  in 'upgrade package' - upgrade selected package and dependencies, if needed.
  in 'upgrade' - upgrade all packages.


TODO
----
- ! write source of requirement (requirements.txt or other package) to frozen.txt then we can check unneeded requirements without installed packages
- ! add vcs support
- add environments support, aka development, testing.
Maybe generate frozen.txt only for pip and use more rich structure for itself?
And put only production packages to frozen.txt, and track all, development and others in frozen.toml?
- ? tie packages only where we need this (C extensions, py2 without __pycache__ support)
- ? bundle distlib (now using one from pip)
- ? bundle pkg_resources (now using one from setuptools)