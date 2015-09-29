#!/usr/bin/env python

from setuptools import setup
import os.path


def read(fname):
    try:
        return open(os.path.join(os.path.dirname(__file__), fname)).read()
    except IOError:
        return ''


setupconf = dict(
    name='pundle',
    version='0.3.2',
    license='BSD',
    url='https://github.com/Deepwalker/pundler/',
    author='Deepwalker',
    author_email='krivushinme@gmail.com',
    description=('Requirements management tool.'),
    long_description=read('README.md'),
    keywords='bundler virtualenv pip install package setuptools',

    py_modules=['pundle'],
    entry_points=dict(
        console_scripts=[
            'pundle = pundle:CmdRegister.main'
        ]
    ),
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ]
)

if __name__ == '__main__':
    setup(**setupconf)
