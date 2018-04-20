import pytest

from legistar import base


@pytest.fixture(scope="module")
def scraper():
    scraper = base.LegistarAPIScraper()
    scraper.BASE_URL = 'http://webapi.legistar.com/v1/chicago'
    scraper.retry_attempts = 0
    scraper.requests_per_minute = 0
    return scraper
