import logging

import scrapelib

from app import settings


class Client(scrapelib.Scraper):
    '''Minimal scrabelib client.
    '''
    def __init__(self, state):

        super(Client, self).__init__()

        # scrapelib setup
        self.timeout = settings.SCRAPELIB_TIMEOUT
        self.requests_per_minute = settings.SCRAPELIB_RPM
        self.retry_attempts = settings.SCRAPELIB_RETRY_ATTEMPTS
        self.retry_wait_seconds = settings.SCRAPELIB_RETRY_WAIT_SECONDS
        self.follow_robots = False

        if state.args.fastmode:
            self.requests_per_minute = 0
            self.cache_write_only = False

        cache_dir = state.configure_cache_dir()
        self.cache_storage = scrapelib.FileCache(cache_dir)

        # logging convenience methods
        self.logger = logging.getLogger('scrapelib')
        self.info = self.logger.info
        self.debug = self.logger.debug
        self.warning = self.logger.warning
        self.error = self.logger.error
        self.critical = self.logger.critical
