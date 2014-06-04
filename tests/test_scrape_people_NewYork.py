import os
from os.path import abspath, dirname, join
import json
import datetime

import lxml.html

from uni import MatchSet
from legistar import get_scraper
from tests.utils import get_fixture, gen_assertions



class TestNewYorkPeople2014:
    DIVISION_ID = 'ocd-division/country:us/state:ny/place:new_york'
    PUPATYPE = 'people'
    YEAR = 2014
    MAX_RECORDS = 10

    def setup(self):
        self.count = 0
        self.scraper = get_scraper(self.DIVISION_ID)
        self.config = self.scraper.config

    def test_output(self):
        view = self.scraper.get_pupatype_searchview(self.PUPATYPE)
        assertions = self.config.gen_assertions(str(self.YEAR), self.PUPATYPE)
        with MatchSet(assertions) as checker:
            for data in view:
                checker.check(data)
                self.count += 1
                if self.MAX_RECORDS < self.count:
                    break
        assert checker.success
