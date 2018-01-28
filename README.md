Pundle
======

[![PyPI](https://img.shields.io/pypi/v/pundle.svg?style=flat-square)](https://pypi.python.org/pypi/pundle)
[![PyPI](https://img.shields.io/pypi/l/pundle.svg?style=flat-square)](https://pypi.python.org/pypi/pundle)


Changelog
---------

- New setup.py support with mocking of setuptools.setup
- Added python shell `try package` feature. To use it use `pundle.use("package_name==0.1")`. Version is optional.
- Added environments support. To use it just make files like `requirement.txt`, `requirements_dev.txt`, `requirements_test.txt`.
  To activate env use like `PUNDLEENV=dev pundle ...`
- Added VCS support for urls like `git+https://github.com/mitsuhiko/jinja2.git@85820fceb83569df62fa5e6b9b0f2f76b7c6a3cf#egg=jinja2-2.8.0`. Push exactly like this formatted str to requirements.txt
- Added initial support for setup.py requirements. Helpful for package development.


What is it all about?
---------------------

Pundle get rid of virtualenv, because I think that virtualenv is pile of garbage
and we must get rid of it.

* Pundle install all packages and its versions to special folder. And mount pinned, frozen
versions on activate step.
* After that you program will use exactly this versions that were pinned in `frozen.txt`.
* If you change branch or edit requirements.txt or frozen.txt, pundle will note you about
you need make install new packages or freeze newly added packages. It will not let you
use packages that have not bin pinned. You will never fall in situation where you test
old version of package.


How to
------

Install:

	> pip install pundle

or just place `pundle.py` where python can find it

Create `requirements.txt` or `setup.py` (we will support .toml a bit later).
You can pin versions if you need it, or just place package name. Pundle will
pin it anyway as well as all of it dependencies.

Reveal all dependencies, pin versions, download and install everything:

	> python -m pundle

Where actually it will install? Pundle use special folder `.pundledir/python-version/package-name-version`
for every seperate package and version.

To make it short create alias:

	alias pundle='/usr/bin/env python -m pundle'
	pundle install

After packages install, frozen/pinned, we want to use them, you know, import, right?

	import pundle; pundle.activate()

Or we can try to use pundle features:

	# to execute entry point
	pundle exec some_package_entry_point
	# to run python script
	pundle run my_script.py
	# run module like python -m
	pundle module some.my.module

To add VCS to `requirements.txt` use `git+url#egg=my_package-0.1.11` form.


Python shell usage
------------------

You can use pundle to expirement in python shell:

	>>> import pundle
	>>> pundle.use('django==1.11.1')  # will download and install django
	>>> import django


Environments
------------

Pundle support environments. You can create seperate requirements file with suffix like
`requirements_dev.txt`. Pundle will create `frozen_dev.txt` that will track common
requirements + dev requirements.

To use `dev` environment use `PUNDLEENV=dev` environment variable:

	bash> PUNDLEENV=dev pundle run myscript.py

or common usage:

	bash> PUNDLEENV=test pundle exec pytest


More usage info
---------------

Upgrade package:

	pundle upgrade django

Upgrade all packages:

	pundle upgrade

List of all entry points:

	pundle entry_points


Do not hesitate to `pundle help` ;)


Howto
-----

Q: How to use custom index url or extra index?
A: use PIP_EXTRA_INDEX_URL or any other `pip` environment variables.
