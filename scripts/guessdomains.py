import re
import os
import csv
import time
import logging
import logging.config
from os.path import join

import scrapelib

path = '/home/thom/sunlight/python-opencivicdata/opencivicdata/division-ids/identifiers/country-us'


class Checker(scrapelib.Scraper):

    OUTFILE = 'domains.csv'
    SCRAPELIB_RPM = 10
    SCRAPELIB_TIMEOUT = 60
    SCRAPELIB_RETRY_ATTEMPTS = 0
    SCRAPELIB_RETRY_WAIT_SECONDS = 20
    FASTMODE = True
    # PROXIES = dict(http="http://localhost", https='https://localhost')
    BOGUS_DOMAIN_MESSAGE = 'Invalid parameters!!'

    def __init__(self):
        super().__init__()
        self.checked_places = set()
        logging.config.dictConfig(self.LOGGING_CONFIG)
        self.logger = logging.getLogger('legistar')

        # scrapelib setup
        self.timeout = self.SCRAPELIB_TIMEOUT
        self.requests_per_minute = self.SCRAPELIB_RPM
        self.retry_attempts = self.SCRAPELIB_RETRY_ATTEMPTS
        self.retry_wait_seconds = self.SCRAPELIB_RETRY_WAIT_SECONDS
        self.follow_robots = False

        # if self.PROXIES:
        #     self.proxies = self.PROXIES

        if self.FASTMODE:
            self.cache_write_only = False

        cache_dir = '.cache'
        self.cache_storage = scrapelib.FileCache(cache_dir)

    def __enter__(self):
        self.outfile = open(self.OUTFILE, 'w')
        self.writer = csv.writer(self.outfile)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.outfile.close()

    def check_all(self):
        for dr, subdrs, filenames in os.walk(path):
            for filename in filenames:
                if 'school' in filename:
                    continue
                if not filename.endswith('.csv'):
                    continue
                self.current_file = filename
                self.logger.warning('Starting file: %r' % filename)
                with open(join(dr, filename), 'r') as csvfile:
                    reader = csv.reader(csvfile)
                    for row in reader:
                        self.row = row
                        self.check_row()

    def check_row(self):
        if not self.row:
            return
        self.ocdid = self.row[0]
        for piece in self.ocdid.split('/'):
            if ':' not in piece:
                continue
            _, place = piece.split(':')
            place = re.sub('[a-z]+[\d\-]+', '', place)
            place = re.sub('[\d\-]+', '', place)
            self.place = self.sluggify(place)
            self.check_place()

    def check_place(self):
        if self.place in self.checked_places:
            return
        if not self.place:
            return
        if '.' in self.place:
            return
        if len(self.place) < 2:
            return
        self.url = 'http://%s.legistar.com' % self.place
        self.logger.debug('Checking %r ...' % self.url)
        resp = self.get(self.url)
        self.checked_places.add(self.place)
        if resp.text.strip() != self.BOGUS_DOMAIN_MESSAGE:
            self.process_hit()
            return True

    def process_hit(self):
        self.logger.warning('HIT: %r' % self.url)
        self.logger.warning('HIT: %r' % self.ocdid)
        data = [self.url]
        self.writer.writerow(data)
        self.outfile.flush()

    def sluggify(self, text):
        return text.replace('_', '').replace('~', '').lower()


    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': "%(asctime)s %(levelname)s %(name)s: %(message)s",
                'datefmt': '%H:%M:%S'
            }
        },
        'handlers': {
            'default': {'level': 'DEBUG',
                        'class': 'legistar.utils.ansistrm.ColorizingStreamHandler',
                        'formatter': 'standard'},
        },
        'loggers': {
            'legistar': {
                'handlers': ['default'], 'level': 'DEBUG', 'propagate': False
            },
            'requests': {
                'handlers': ['default'], 'level': 'DEBUG', 'propagate': False
            },
        },
    }


if __name__ == '__main__':
    with Checker() as checker:
        checker.check_all()



