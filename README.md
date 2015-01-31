Pundler
=======

Python bundler-alike alternative to virtualenv. Best play with pyenv.

For now works only with PyPI packages.
Git, svn and so on support planned to support a bit later.

Now this is expirement, but very cool one.

Prerequisites
-------------

- I recommend use pyenv
- install setuptools if you python distribution has not
- pundler needs pip


Commands
--------

`pundler [install]` will install files from freezed.txt file and reveal
    new requirements if something not freezed yet.

`pundler upgrade` will recreate freezed.txt from requirements.txt

`pundler fixate` installs site costumization for current python

`pundler exec cmd [args]` executes entry point from one os the installed packages

`pundler entry_points` prints entry points from all packages

`pundler edit` returns path to package directory


How to play with it
-------------------

    git clone git@github.com:Deepwalker/pundler.git
    python pundler/pundler.py fixate

    cd testproject
    python -m pundler upgrade

Pundler will create directory `Pundledir` and file `freezed.txt`.


DONE
----
- install by freezed.txt
- on update rewrite freezed.txt
- on launch check if freezed.txt is in touch with requirements.txt
- Search through hierarchy upward
- tie packages to python version.
- package scripts
- upgrade must lookup PyPI for new version
- In basic freeze mode if req have not freeze, then install latest package from PyPI. Else install freezed version.
  In 'upgrade package' - upgrade selected package and dependencies, if needed.
  In 'upgrade' - upgrade all packages.


TODO
----
- ! write cause to freezed.txt then we can check unneeded requirements without installed packages
- ! add vcs support
- add environment support, aka developmment, testing
Maybe generate freezed.txt only for pip and use more rich structure for itself?
And put only production packages to freezed.txt, and track all, development and others in freezed.toml?
- ? tie packages only where we need this (C extensions, py2 without __pycache__ support)
- ? bundle distlib (now using one from pip)
- ? bundle pkg_resources (now using one from setuptools)