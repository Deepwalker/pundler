Pundle
======

[![PyPI](https://img.shields.io/pypi/dm/pundle.svg?style=flat-square)](https://pypi.python.org/pypi/pundle)
[![PyPI](https://img.shields.io/pypi/v/pundle.svg?style=flat-square)](https://pypi.python.org/pypi/pundle)
[![PyPI](https://img.shields.io/pypi/l/pundle.svg?style=flat-square)](https://pypi.python.org/pypi/pundle)

New
---

- Added VCS support for urls like `git+https://github.com/mitsuhiko/jinja2.git@85820fceb83569df62fa5e6b9b0f2f76b7c6a3cf#egg=jinja2-2.8.0`. Push exactly like this formatted str to requirements.txt
- Added initial support for setup.py requirements. Helpful for package development.


Modern python package management for python development
-------------------------------------------------------

For development we need two things — the right python interpreter and the right
package versions.

We can get the interpreter via the system package manager: brew, apt, yum etc.
You can even install some packages with the system manager, but quickly you get
to the point where repositories don't contain the package versions you need. And
often you're in the situation where the system doesn't have the current
interpreter version.

And even worse is situation when you develop several projects and every project
needs a different interpreter and indeed every project needs its own versions of
packages.

The packages situation was initially solved by _virtualenv_. It's not the best
solution but it works.

The interpreter situation has been solved well by the
[pyenv](https://github.com/yyuu/pyenv) project. If you're not familiar with it,
it enables you to install as many interpreters as you need. All of them are
separated and system behavior isn't augmented:

```bash
> brew install pyenv
> pyenv install 3.4.1
  ... installing
> pyenv shell 3.4.1
> python --version
  Python 3.4.1
```

This interpreter is completely independent from your system's. When you activate
it in your shell, it will become the current python interpreter. It can also be
configured per-project via the `.pyenv-version` file.

Using pyenv as an example to create Pundle
------------------------------------------

So, it's cool, I like how pyenv works. But we all know that pyenv works similarly
to how rbenv works for ruby.

If we're borrowing the rbenv concept from ruby, why not also borrow
[Bundler](http://bundler.io/)? It works like this:

You write a `Gemfile`, listing packages your app depends on, similar to
`requirements.txt`. Generally, they're not pegged too tightly to specific versions,
although they can be. Next, you execute `bundle install` and if you don't yet have
a `Gemfile.lock` it will create one, resolving all dependencies, and
listing the nailed-down package versions that play nice with your `Gemfile`. Finally,
it will install the specific packages listed in `Gemfile.lock`.

And when you startup a rails application with `bundle exec rails server`,
bundler looks into the project's `Gemfile.lock` and loads the appropriate
package versions.

If you switch the branch and your `Gemfile.lock` changes, the packages will be
switched too. This is not magic — we just load versions according to the file.

And in my opinion this is the right way to do it, and something that we need in
python. I don't like to rebuild virtualenvs, I don't understand why I need them
anyway. E.g., why do I need to install Django in every single one of my
projects?

So I created `Pundle`.

Pundle
------

The main goal of pundle is activating the right package versions upon
interpreter startup. To activate the machinery we have several options:

* use `fixate` which will put activate code in `usercustomize.py` in the user's
  directory
* use `python -m pundle run script.py` to run script with activated environment
* put activate code `import pundle; pundle.activate()` to your `manage.py` or
  other project start point.


Personaly I prefer `run`:

    # activate python, if still have not .pyenv-version
    > pyenv shell 3.4.1
    > python -m pip install pundle

And we are ready to install packages from your requirements.txt:

    > python -m pundle install
    ... long work here

And you will get `frozen.txt` file with frozen packages versions and some information:

    alembic==0.7.4       # alembic << requirements file
    arrow==0.5.0         # arrow << requirements file
    awesome-slugify==1.6 # awesome-slugify << requirements file
    babel==1.3           # Babel>=1.0 << Flask-Babel << requirements file
    dawg-python==0.7.1   # dawg-python>=0.7 << pymorphy2 << requirements file
    docopt==0.6.2        # docopt>=0.6 << pymorphy2 << requirements file


Now your packages are installed to the `~/.pundlerdir/CPython-3.4.1` directory.
And you can use it with your fixated python:

    > python -m pundle console
    ... bla bla bla 3.4.1
    >>> import arrow
    >>> arrow.__version__
    '0.5.0'

Pundle gets frozen version from `frozen.txt`, and activates package from ~/.pundledir/CPython-3.4.1-default/arrow-0.5.0/

    >>> arrow.__file__
    '/Users/mighty_user/.pundledir/CPython-3.4.1-default/arrow-0.5.0/arrow/__init__.py'

And execute for project:

    > python -m pundle run manage.py runserver


Going deeper
------------

We have additional commands for working with packages. `upgrade`, `entry_points`, `exec` and `edit`.

If your frozen versions of a package is old and you want to update it, you need the `upgrade` command:

    > python -m pundle upgrade django

Or you can update all packages:

    > python -m pundle upgrade

`entry_points` will show you all commands that your packages offer you:

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

Last command is `edit` - it will help you find fast where the package code is:

    > python -m pundle edit arrow
    /Users/main_universe_user/.pundledir/CPython-3.4.1-default/arrow-0.5.0

Use it, feel it, like it, share it. Commit, pull request.
