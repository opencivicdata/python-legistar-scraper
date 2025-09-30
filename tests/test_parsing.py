import os

import lxml
import pytest

from src.legistar.ui.bills import LegistarBillScraper
from src.legistar.ui.events import LegistarEventsScraper
from src.legistar.ui.people import LegistarPersonScraper


@pytest.mark.parametrize('jurisdiction', ['chicago', 'metro', 'nyc'])
def test_parse_bills(project_directory, jurisdiction):
    bills_fixture = os.path.join(project_directory, 'tests', 'fixtures', jurisdiction, 'bills.html')

    scraper = LegistarBillScraper()
    scraper.BASE_URL = '{}.legistar.com'.format(jurisdiction)

    with open(bills_fixture, 'r') as f:
        page = lxml.html.fromstring(f.read())
        result = next(scraper.parse_search_results(page))
        print(result)


@pytest.mark.parametrize('jurisdiction', ['chicago', 'metro', 'nyc'])
def test_parse_events(project_directory, mocker, jurisdiction):
    events_fixture = os.path.join(project_directory, 'tests', 'fixtures', jurisdiction, 'events.html')

    scraper = LegistarEventsScraper()
    scraper.BASE_URL = '{}.legistar.com'.format(jurisdiction)

    with open(events_fixture, 'r') as f:
        page = lxml.html.fromstring(f.read())
        mocker.patch.object(scraper, 'event_pages', return_value=page)
        result, _ = next(scraper.events(follow_links=False))
        print(result)


@pytest.mark.parametrize('jurisdiction', ['chicago', 'metro', 'nyc'])
def test_parse_people(project_directory, mocker, jurisdiction):
    events_fixture = os.path.join(project_directory, 'tests', 'fixtures', jurisdiction, 'people.html')

    scraper = LegistarPersonScraper()
    scraper.BASE_URL = '{}.legistar.com'.format(jurisdiction)

    with open(events_fixture, 'r') as f:
        page = lxml.html.fromstring(f.read())
        mocker.patch.object(scraper, 'pages', return_value=page)
        result = next(scraper.council_members(follow_links=False))
        print(result)
