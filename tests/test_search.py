import pytest


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
