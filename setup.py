#!/usr/bin/env python
from setuptools import setup
from legistar import __version__

long_description = ''

setup(name='scraper-legistar',
      version=__version__,
      packages=['legistar'],
      author='Forest Gregg',
      author_email='fgregg@datamade.us',
      license='BSD',
      url='http://github.com/opencivicdata/python-legistar-scraper/',
      description='Mixin classes for legistar scrapers',
      long_description=long_description,
      platforms=['any'],
      install_requires=['requests',
                        'lxml',
                        'pytz',
                        'icalendar',
                        'scrapelib',
                        'esprima'
                        ],
      classifiers=["Development Status :: 4 - Beta",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Natural Language :: English",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python :: 3.3",
                   "Programming Language :: Python :: 3.4",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   ],
      )
