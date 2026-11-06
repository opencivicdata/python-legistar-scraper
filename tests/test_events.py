from unittest import mock

import lxml.html
import pytest
import requests
import scrapelib

from legistar.events import LegistarAPIEventScraper


class ChicagoAPIEventScraper(LegistarAPIEventScraper):
    BASE_URL = 'https://webapi.legistar.com/v1/chicago'
    WEB_URL = 'https://chicago.legistar.com'
    EVENTSPAGE = 'https://chicago.legistar.com/Calendar.aspx'
    TIMEZONE = 'America/Chicago'


@pytest.fixture
def api_event_scraper():
    scraper = ChicagoAPIEventScraper()
    scraper.retry_attempts = 0
    scraper.requests_per_minute = 0
    return scraper


@pytest.fixture
def api_event():
    return {'EventInSiteURL': 'https://chicago.legistar.com/MeetingDetail.aspx?ID=1'}


def http_error(status_code):
    response = requests.Response()
    response.status_code = status_code
    return scrapelib.HTTPError(response)


@pytest.mark.parametrize('status_code', [410, 500, 502, 503, 504])
def test_web_detail_skips_gone_and_server_errors(api_event_scraper, api_event, status_code):
    with mock.patch.object(api_event_scraper._webscraper, 'lxmlize',
                           side_effect=http_error(status_code)):
        assert api_event_scraper.web_detail(api_event) is None


def test_web_detail_raises_other_client_errors(api_event_scraper, api_event):
    with mock.patch.object(api_event_scraper._webscraper, 'lxmlize',
                           side_effect=http_error(404)):
        with pytest.raises(scrapelib.HTTPError):
            api_event_scraper.web_detail(api_event)


def test_web_detail_skips_page_without_details(api_event_scraper, api_event):
    page = lxml.html.fromstring('<html><body><p>Under maintenance</p></body></html>')
    with mock.patch.object(api_event_scraper._webscraper, 'lxmlize',
                           return_value=page):
        assert api_event_scraper.web_detail(api_event) is None
