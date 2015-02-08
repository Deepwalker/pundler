Pundle
======


Modern python package management for python development
-------------------------------------------------------

For development we need two things - right python interpreter
and right packages versions.

We can get interpreter by system package manager - brew, apt, yum etc.
You can even install some packages with system manager, but
quickly you get to the point where repositories are not contain
appropriate package version. And now you are often in situation
when system has not actual interpreter version.

And even worse is situation when you develop several projects
and every project need different interpreter and indeed every
project need its own versions of packages.

Packages situation were solved with virtualenv. Its not best solution
but it works.

Interpreter situation is solved now with [pyenv](https://github.com/yyuu/pyenv)
project. You can install as many interpreters as you need
and all of them are separated and does not augument system
behaviour:

    > brew install pyenv
    > pyenv install 3.4.1
    ... installing
    > pyenv shell 3.4.1
    > python --version
    Python 3.4.1

This interpreter is completely independent from your system, and
you activate it in your shell and it will switch python version
for your according to projects ``.pyenv-version`` file.


So, its cool, I like how pyenv works. But we all know that pyenv
works similar to how rbenv works for ruby.

If we grab rbenv from ruby, why no to grab Bundler project?
How it like, you have a ``Gemfile``, with packages description.
Then you call ``bundler install`` and if you have not ``Gemfile.lock``
it will install latest packages versions that play nice with your ``Gemfile``
or if you have ``Gemfile.lock`` it will install packages according it.

And when you start you rails application with ``bundle exec rails s``
bundler looking into projects ``Gemfile.lock`` and loads appropriate
packages versions.

If you switch branch and your ``Gemfile.lock`` changes, packages will be switched too,
and this is not magic - we just load versions according to file.

And in my opinion this is a right thing, and something that we need in python.
I dont like to rebuild virtualenvs, I dont understand why I need them anyway.
Why I need to install Django number of my projects times.

So I created ``Pundle``.

Pundle
------

Main goal of pundle is activating right packages versions on interpreter start.
To activate machinery we have several ways:
    - use ``fixate`` that will put activate code to the usercustomize.py in user directory
    - use ``python -m pundle run script.py`` to run script with acitvated environment
    - put activate code ``import pundle; pundle.activate()`` to your ``manage.py`` or other project start point.


Personaly I prefer ``run``:

    # activate python, if still have not .pyenv-version
    > pyenv shell 3.4.1
    > python -m pip install pundle

And we are ready to install packages from your requirements.txt:

    > python -m pundle install
    ... long work here

And you will get ``frozen.txt`` file with frozen packages versions and some information:

    alembic==0.7.4       # alembic << requirements file
    arrow==0.5.0         # arrow << requirements file
    awesome-slugify==1.6 # awesome-slugify << requirements file
    babel==1.3           # Babel>=1.0 << Flask-Babel << requirements file
    dawg-python==0.7.1   # dawg-python>=0.7 << pymorphy2 << requirements file
    docopt==0.6.2        # docopt>=0.6 << pymorphy2 << requirements file


Now your packages are install to the ``~/.pundlerdir/CPython-3.4.1`` directory.
And you can use it with your fixated python:

    > python -m pundle console
    ... bla bla bla 3.4.1
    >>> import arrow
    >>> arrow.__version__
    '0.5.0'

Pundle get frozen version from ``frozen.txt``, and activate package from ~/.pundledir/CPython-3.4.1-default/arrow-0.5.0/

    >>> arrow.__file__
    '/Users/mighty_user/.pundledir/CPython-3.4.1-default/arrow-0.5.0/arrow/__init__.py'

And execute fof project:

    > python -m pundle run manage.py runserver


Going deeper
------------

We have additional commands for working with packages. ``upgrade``, ``entry_points``, ``exec`` and ``edit``.

If you frozen versions of package is old and you want to update it, you need ``upgrade`` command:

    > python -m pundle upgrade django

Or you can update all packages:

    > python -m pundle upgrade

``entry_points`` will show you all commands that your packages offer you:

    > python -m pundle entry_points
    nomad (nomad 1.9)
    gunicorn_paster (gunicorn 19.2.0)
    gunicorn_django (gunicorn 19.2.0)
    mako-render (Mako 1.0.1)
    webassets (webassets 0.10.1)
    alembic (alembic 0.7.4)
    pyflakes (pyflakes 0.8.1)
    pyscss (pyScss 1.3.4)
    pybabel (Babel 1.3)
    gunicorn (gunicorn 19.2.0)

And of course we have command to start this command:

    > python -m pundle exec pyflakes start.py
    start.py:2: 'url_for' imported but unused

Last command is ``edit`` - it will help you find fast where the package code is:

    > python -m pundle edit arrow
    /Users/main_universe_user/.pundledir/CPython-3.4.1-default/arrow-0.5.0

Use it, feel it, like it, share it. Commit, pull request.
