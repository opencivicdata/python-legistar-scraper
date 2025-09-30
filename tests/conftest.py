import json
import os

import pytest

from src.legistar.api import base
from src.legistar.api.bills import LegistarAPIBillScraper


@pytest.fixture(scope="module")
def scraper():
    scraper = base.LegistarAPIScraper()
    scraper.BASE_URL = "http://webapi.legistar.com/v1/chicago"
    scraper.retry_attempts = 0
    scraper.requests_per_minute = 0
    return scraper


@pytest.fixture
def project_directory():
    test_directory = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(test_directory, "..")


@pytest.fixture
def fixtures_directory():
    test_directory = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(test_directory, "fixtures")


@pytest.fixture
def metro_api_bill_scraper():
    scraper = LegistarAPIBillScraper()
    scraper.BASE_URL = "https://webapi.legistar.com/v1/metro"
    scraper.retry_attempts = 0
    scraper.requests_per_minute = 0
    return scraper


@pytest.fixture
def chicago_api_bill_scraper():
    scraper = LegistarAPIBillScraper()
    scraper.BASE_URL = "https://webapi.legistar.com/v1/chicago"
    scraper.retry_attempts = 0
    scraper.requests_per_minute = 0
    return scraper


@pytest.fixture
def matter_index(fixtures_directory):
    fixture_file = os.path.join(fixtures_directory, "metro", "matter_index.json")
    with open(fixture_file, "r") as f:
        fixture = json.load(f)
    return fixture


@pytest.fixture
def all_indexes(fixtures_directory):
    fixture_file = os.path.join(fixtures_directory, "metro", "all_indexes.json")
    with open(fixture_file, "r") as f:
        fixture = json.load(f)
    return fixture


@pytest.fixture
def dupe_event(fixtures_directory):
    fixture_file = os.path.join(fixtures_directory, "chicago", "dupe_event.json")
    with open(fixture_file, "r") as f:
        fixture = json.load(f)
    return fixture


@pytest.fixture
def no_dupe_event(fixtures_directory):
    fixture_file = os.path.join(fixtures_directory, "chicago", "no_dupe_event.json")
    with open(fixture_file, "r") as f:
        fixture = json.load(f)
    return fixture
