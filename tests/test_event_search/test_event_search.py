import os
from os.path import abspath, dirname, join
import json
import datetime

import lxml.html

from uni import MatchSet
from legistar import get_scraper
from tests.utils import get_fixture, gen_assertions


class Base:

    OCD_ID = None
    FILENAME = None



class TestNewYork(Base):
    OCD_ID = 'ocd-division/country:us/state:ny/place:new_york'

    def __init__(self):
        self.scraper = get_scraper(self.OCD_ID)
        self.config = self.scraper.config
        self.config.USING_TEST_CONFIG = True
        self.host = self.config.get_host()
        self.doc = get_fixture(self.host, self.FILENAME)

    def gen_assertions(self):
        yield from gen_assertions(host, 'test_event_search')

    # def test_events_search(self):
    #     view = self.scraper.get_pupatype_searchview('events', doc=self.doc)
    #     with MatchSet(self.assertions) as checker:
    #         for data in view.Form():
    #             checker.check(data)
    #     assert checker.success

    def test_events_search(self):
        import pdb; pdb.set_trace()
        view = self.scraper.get_pupatype_searchview('events', doc=self.doc)
        with MatchSet(self.assertions) as checker:
            for data in view.Form():
                checker.check(data)
        assert checker.success

