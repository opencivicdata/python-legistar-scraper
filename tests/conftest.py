import os

import pytest

from legistar import base


@pytest.fixture(scope="module")
def scraper():
    scraper = base.LegistarAPIScraper()
    scraper.BASE_URL = 'http://webapi.legistar.com/v1/chicago'
    scraper.retry_attempts = 0
    scraper.requests_per_minute = 0
    return scraper


@pytest.fixture
def project_directory():
    test_directory = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(test_directory, '..')
