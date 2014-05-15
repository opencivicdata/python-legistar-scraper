#!/usr/bin/env python

from setuptools import find_packages, setup

long_description = """Basic regular expression lexer implementation.
"""

appname = "rexlex"
version = "0.00"

setup(**{
    "name": appname,
    "version": version,
    "packages": [
        'tater',
        ],
    "author": "Thom Neale",
    "packages": find_packages(exclude=['tests*']),
    "package_data": {
        'rexlex.lexer': ['*.py'],
        'rexlex.scanner': ['*.py'],
        },
    "author_email": "twneale@gmail.com",
    "long_description": long_description,
    "description": 'Basic regular expression lexer implementation.',
    "license": "MIT",
    "url": "http://twneale.github.com/rexlex/",
    "platforms": ['any'],
    "scripts": [
    ]
})
