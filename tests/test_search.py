import pytest

from legistar import base

@pytest.fixture(scope="module")
def scraper():
    scraper = base.LegistarAPIScraper(None, None)
    scraper.BASE_URL = 'http://webapi.legistar.com/v1/chicago'
    scraper.retry_attempts = 0
    scraper.requests_per_minute = 0
    return scraper


class TestAPISearch(object):

    def test_search_raises(self, scraper):
        with pytest.raises(ValueError):
            results = scraper.search('/events/', 'EventId',
                                     "MatterFile eq 'O2010-5046'")
            list(results)
            
    def test_search(self, scraper):
        results = scraper.search('/matters/', 'MatterId',
                                 "MatterFile eq 'O2010-5046'")
        
        
        assert len(list(results)) == 1
