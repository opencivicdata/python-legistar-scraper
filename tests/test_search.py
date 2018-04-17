import unittest

import pytest

from legistar import base


class TestAPISearch(unittest.TestCase):

    def setUp(self):
        self.scraper = base.LegistarAPIScraper(None, None)
        self.scraper.BASE_URL = 'http://webapi.legistar.com/v1/chicago'
        self.scraper.retry_attempts = 0
        self.scraper.requests_per_minute = 0
        
    def test_search_raises(self):
        with pytest.raises(ValueError):
            results = self.scraper.search('/events/', 'EventId',
                                          "MatterFile eq 'O2010-5046'")
            list(results)
            
    def test_search(self):
        results = self.scraper.search('/matters/', 'MatterId',
                                      "MatterFile eq 'O2010-5046'")
        
        
        assert len(list(results)) == 1
