======
Pundle
======

|circleci_build| |pypi_version| |pypi_license|

Changelog
---------

-  Pipfile initial support. Only strings as versions now.
   Do not calculates hashes and do not use it yet.
-  New setup.py support with mocking of setuptools.setup
-  Added python shell ``try package`` feature. To use it use
   ``pundle.use("package_name==0.1")``. Version is optional.
-  Added environments support. To use it just make files like
   ``requirement.txt``, ``requirements_dev.txt``,
   ``requirements_test.txt``. To activate env use like
   ``PUNDLEENV=dev pundle ...``
-  Added VCS support for urls like
   ``git+https://github.com/mitsuhiko/jinja2.git@85820fceb83569df62fa5e6b9b0f2f76b7c6a3cf#egg=jinja2-2.8.0``.
   Push exactly like this formatted str to requirements.txt
-  Added initial support for setup.py requirements. Helpful for package
   development.

What is it all about?
---------------------

Pundle get rid of virtualenv, because I think that virtualenv is pile of
garbage and we must get rid of it.

-  Pundle install all packages and its versions to special folder. And
   mount pinned, frozen versions on activate step.
-  After that you program will use exactly this versions that were
   pinned in ``frozen.txt``.
-  If you change branch or edit requirements.txt or frozen.txt, pundle
   will note you about you need make install new packages or freeze
   newly added packages. It will not let you use packages that have not
   bin pinned. You will never fall in situation where you test old
   version of package.

Why not Pipenv, I heard it is "for humans"?
-----------------------------------------

I don't think that anything that is based on virtualenv can be "for humans". And
pundle far more friendly and supportive even without all this hype and with one dev.

How to
------

Install:

.. code-block:: bash

    > pip install pundle

or just place ``pundle.py`` where python can find it

Create ``requirements.txt`` or ``setup.py`` (we will support .toml a bit
later). You can pin versions if you need it, or just place package name.
Pundle will pin it anyway as well as all of it dependencies.

Reveal all dependencies, pin versions, download and install everything:

.. code-block:: bash

    > python -m pundle

Where actually it will install? Pundle use special folder
``.pundledir/python-version/package-name-version`` for every seperate
package and version.

To make it short create alias:

.. code-block:: bash

    alias pundle='/usr/bin/env python -m pundle'
    pundle install

After packages install, frozen/pinned, we want to use them, you know,
import, right?

.. code-block:: python

    import pundle; pundle.activate()

Or we can try to use pundle features:

.. code-block:: bash

    # to execute entry point
    pundle exec some_package_entry_point
    # to run python script
    pundle run my_script.py
    # run module like python -m
    pundle module some.my.module

To add VCS to ``requirements.txt`` use ``git+url#egg=my_package-0.1.11``
form.


Pundle console
--------------

To start console with Pundle activated use

.. code-block:: bash

    > pundle console [ipython|ptpython|bpython]

You will have ``pundle_suite`` object inserted to environment. You can use it
to call ``pundle_suite.use("trafaret_schema")`` for example.


Python shell usage
------------------

You can use pundle to expirement in python shell:

.. code-block:: python

    >>> import pundle
    >>> pundle.use('django==1.11.1')  # will download and install django
    >>> import django

Or you can use it in script:

.. code-block:: python

    >>> import pundle
    >>> pundle.use('django')
    >>> pundle.use('arrow')
    >>> pundle.use('trafaret')
    >>>
    >>> import django
    >>> import arrow
    >>> import trafaret

Environments
------------

Pundle support environments. You can create seperate requirements file
with suffix like ``requirements_dev.txt``. Pundle will create
``frozen_dev.txt`` that will track common requirements + dev
requirements.

To use ``dev`` environment use ``PUNDLEENV=dev`` environment variable:

.. code-block:: bash

    bash> PUNDLEENV=dev pundle run myscript.py

or common usage:

.. code-block:: bash

    bash> PUNDLEENV=test pundle exec pytest

For ``setup.py`` file pundle uses ``extras_require`` as environments. For example if
you have ``extras_require = {'test': ['pylint', 'pyflakes']}`` then you can use
``pylint`` with ``PUNDLEENV=test pundle exec pylint``.

More usage info
---------------

Upgrade package:

.. code-block:: bash

    pundle upgrade django

Upgrade all packages:

.. code-block:: bash

    pundle upgrade

List of all entry points:

.. code-block:: bash

    pundle entry_points

Do not hesitate to ``pundle help`` ;)

Howto
-----

Q: How to use custom index url or extra index?

A: use PIP_EXTRA_INDEX_URL or any other ``pip`` environment variables.

.. |circleci_build| image:: https://circleci.com/gh/Deepwalker/pundler.svg?style=svg
   :target: https://circleci.com/gh/Deepwalker/pundler
.. |pypi_version| image:: https://img.shields.io/pypi/v/pundle.svg?style=flat-square
   :target: https://pypi.python.org/pypi/pundle
.. |pypi_license| image:: https://img.shields.io/pypi/l/pundle.svg?style=flat-square
   :target: https://pypi.python.org/pypi/pundle
