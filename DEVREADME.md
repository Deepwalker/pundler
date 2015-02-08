Pundle
=======

![Pundle](/pundle.png?raw=true "Pundle")

Pundle is bunder-like replacement of virtualenv for developers and works great with pyenv.
It is not recommended to use Pundle for deployment (it was created for different purpose)
and currently only works with PyPI packages. Git, SVN and other package sources will be added later.

For now works only with PyPI packages.
Git, svn and others support planned.


Small workflow example:

    # install it to site-packages for simplicity now (recommend use *sh alias and dedicated folder with git checkout)
    > pip install pundle
    # finished with virtualenv or python site-packages pollution, all packages will be in ~/.pundledir
    # now long long time ago in one far far away project
    > echo "Django" > requirements.txt
    > pundle install
    > cat frozen.txt
    Django==1.6
    > python manage.py runserver
    CTRL-C
    ... long work with project

    # You want a refactoring and migrate to new framwork version.
    # Your project has some incompatibility bugs now
    > git checkout -b new_django_version
    > pundle upgrade
    > cat frozen.txt
    Django==1.7.4
    ... work hard for sometime

    # Now you have alarm on production branch
    > git commit -a -m 'Fixed first part of bugs with last django'
    > git checkout master
    > python manage.py runserver

Feel it - you need not to remove virtualenv, or switch it, or anything else. Pundle look into
frozen.txt and activate that versions of packages that you need right now. You switch branch -
package version switched with you.

Pundle not about tracking requirements and filling frozen.txt with double-equals signs - its about
importing right version of package in right place.



Prerequisites
-------------

- I recommend using pyenv
- requires setuptools
- requires pip


Commands
--------

`pundle [install]` will install files from frozen.txt file and reveal
    new requirements if something is not frozen yet.

`pundle upgrade` will recreate frozen.txt from requirements.txt.

`pundle fixate` installs site customization for current python.

`pundle exec cmd [args]` executes entry point from one of the installed packages.

`pundle entry_points` prints entry points from all packages.

`pundle edit [package]` returns path to package directory.


How to play with it
-------------------

Simple with usercustomize.py:

    git clone git@github.com:Deepwalker/pundler.git
    python pundler/pundle.py fixate

    cd testproject
    python -m pundle upgrade

Pundle will create directory `~/.pundledir` and file `frozen.txt`.

Or you can make ``alias pundle='python /full/path/to/pundle/pundle.py'`` and use it.
And add ``/full/path/to/pundle`` to your ``PYTHONPATH``.
But you will need to manual load dependencies in your project start script, like this:

    import pundle; pundle.activate()

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