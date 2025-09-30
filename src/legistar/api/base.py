import datetime
from collections import deque
import requests
import logging

import scrapelib
import pytz


class LegistarAPIScraper(scrapelib.Scraper):
    date_format = '%Y-%m-%dT%H:%M:%S'
    time_string_format = '%I:%M %p'
    utc_timestamp_format = '%Y-%m-%dT%H:%M:%S.%f'

    def __init__(self, *args, **kwargs):
        super(LegistarAPIScraper, self).__init__(*args, **kwargs)
        self.logger = logging.getLogger("legistar")
        self.warning = self.logger.warning

    def to_time(self, text):
        time = datetime.datetime.strptime(text, self.date_format)
        time = pytz.timezone(self.TIMEZONE).localize(time)
        return time

    def to_utc_timestamp(self, text):
        try:
            time = datetime.datetime.strptime(text, self.utc_timestamp_format)
        except ValueError as e:
            if 'does not match format' in str(e):
                time = datetime.datetime.strptime(text, self.date_format)
            else:
                raise
        time = pytz.timezone('UTC').localize(time)
        return time

    def search(self, route, item_key, search_conditions):
        """
        Base function for searching the Legistar API.

        Arguments:

        route -- The path to search, i.e. /matters/, /events/, etc
        item_key -- The unique id field for the items that you are searching.
                    This is necessary for proper pagination. examples
                    might be MatterId or EventId
        search_conditions -- a string in the OData format for the
                             your search conditions
                             http://www.odata.org/documentation/odata-version-3-0/url-conventions/#url5.1.2

                             It would be nice if we could provide a
                             friendly search API. Something like
                             https://github.com/tuomur/python-odata


        Examples:
        # Search for bills introduced after Jan. 1, 2017
        search('/matters/', 'MatterId', "MatterIntroDate gt datetime'2017-01-01'")
        """

        search_url = self.BASE_URL + route

        params = {'$filter': search_conditions}

        try:
            yield from self.pages(search_url,
                                  params=params,
                                  item_key=item_key)
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                raise ValueError(e.response.json()['Message'])
            if not self.accept_response(e.response):
                raise

    def pages(self, url, params=None, item_key=None):
        if params is None:
            params = {}

        seen = deque([], maxlen=1000)

        page_num = 0
        response = None
        while page_num == 0 or len(response.json()) == 1000:
            params['$skip'] = page_num * 1000
            response = self.get(url, params=params)
            response.raise_for_status()

            for item in response.json():
                if item[item_key] not in seen:
                    yield item
                    seen.append(item[item_key])

            page_num += 1

    def accept_response(self, response, **kwargs):
        """
        This overrides a method that controls whether
        the scraper should retry on an error. We don't
        want to retry if the API returns a 400, except for
        410, which means the record no longer exists.
        """
        return response.status_code < 401 or response.status_code == 410
