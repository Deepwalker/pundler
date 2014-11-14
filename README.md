Pundler
=======

Python bundler-alike alternative to virtualenv.

For now works only with PyPI packages.
Git, svn and so on support planned to support a bit later.

Now this is expirement.



How to play with it
-------------------

    git clone git@github.com:Deepwalker/pundler.git
    cd pundler
    git submodules init

    cd <project directory>
    create requirements.txt
    python3.4 <path to pundler>/pundler.py

Pundler will create directory `Pundledir` and file `freezed.txt`.
