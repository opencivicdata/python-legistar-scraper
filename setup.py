#!/usr/bin/env python

from setuptools import find_packages, setup

long_description = """A configurable scraper for the Legistar CMS.
"""

appname = "legistar"
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
        'legistar.jurisdictions': ['*.py'],
        'legistar.utils': ['*.py'],
        },
    "entry_points": '''[console_scripts]
legistar = legistar.cli:run''',
    "author_email": "twneale@gmail.com",
    "long_description": long_description,
    "description": 'A scraper for Legistar websites.',
    "license": "MIT",
    "url": "http://github.com/sunlightlabs/legistar/",
    "platforms": ['any'],
    "install_requires": [
        'nmmd',
    ],
    "classifiers": [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4"]
})
