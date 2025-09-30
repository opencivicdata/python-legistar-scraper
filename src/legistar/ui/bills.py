from .base import LegistarScraper
from lxml.etree import tostring
from collections import deque


class LegistarBillScraper(LegistarScraper):
    def legislation(self, search_text='', created_after=None,
                    created_before=None):

        # If legislation is added to the the legistar system while we
        # are scraping, it will shift the list of legislation down and
        # we might revisit the same legislation. So, we keep track of
        # the last few pieces of legislation we've visited in order to
        # make sure we are not revisiting
        scraped_leg = deque([], maxlen=10)

        for page in self.search_legislation(search_text, created_after,
                                           created_before):
            for legislation_summary in self.parse_search_results(page):
                if not legislation_summary['url'] in scraped_leg:
                    yield legislation_summary
                    scraped_leg.append(legislation_summary['url'])

    def search_legislation(self, search_text='', created_after=None,
                          created_before=None):
        """
        Submit a search query on the legislation search page, and return a list
        of summary results.
        """

        page = self.lxmlize(self.LEGISLATION_URL)

        page = self._advancedSearch(page)

        payload = {}

        # Enter the search parameters TODO: Each of the possible form
        # fields should be represented as keyword arguments to this
        # function. The default query string should be for the the
        # default 'Legislative text' field.
        payload['ctl00$ContentPlaceHolder1$txtText'] = search_text

        if created_after and created_before:
            payload.update(date_within(created_after, created_before))

        elif created_before:
            payload.update(date_bound(created_before))
            payload['ctl00$ContentPlaceHolder1$radFileCreated'] = '<'

        elif created_after:
            payload.update(date_bound(created_after))
            payload['ctl00$ContentPlaceHolder1$radFileCreated'] = '>'

        # Return up to one million search results
        payload['ctl00_ContentPlaceHolder1_lstMax_ClientState'] = '{"value":"1000000"}'
        payload['ctl00_ContentPlaceHolder1_lstYearsAdvanced_ClientState'] = '{"value":"All"}'
        payload['ctl00$ContentPlaceHolder1$btnSearch'] = 'Search Legislation'

        payload.update(self.session_secrets(page))

        return self.pages(self.LEGISLATION_URL, payload)

    def parse_search_results(self, page):
        """Take a page of search results and return a sequence of data
        of tuples about the legislation, of the form

        ('Document ID', 'Document URL', 'Type', 'Status', 'Introduction Date'
        'Passed Date', 'Main Sponsor', 'Title')
        """
        table = page.xpath(
            "//table[@id='ctl00_ContentPlaceHolder1_gridMain_ctl00']")[0]
        for legislation, headers, row in self.parse_data_table(table):
            # Do legislation search-specific stuff
            # ------------------------------------
            # First column should be the ID of the record.
            id_key = headers[0]
            try:
                legislation_id = legislation[id_key]['label']
            except TypeError:
                continue
            legislation_url = legislation[id_key]['url'].split(
                self.BASE_URL)[-1]
            legislation[id_key] = legislation_id
            legislation['url'] = self.BASE_URL + \
                legislation_url.split('&Options')[0] + '&FullText=1'

            yield legislation

    def _advancedSearch(self, page):
        search_switcher = page.xpath(
            "//input[@id='ctl00_ContentPlaceHolder1_btnSwitch']")[0]

        if 'simple search' in search_switcher.value.lower():
            return page
        else:
            payload = self.session_secrets(page)
            payload[search_switcher.name] = search_switcher.value

            page = self.lxmlize(self.LEGISLATION_URL, payload)

            if 'simple search' not in page.xpath("//input[@id='ctl00_ContentPlaceHolder1_btnSwitch']")[0].value.lower():
                raise ValueError('Not on the advanced search page')

            return page

    def details(self, detail_url, div_id):
        detail_page = self.lxmlize(detail_url)

        detail_div = detail_page.xpath(".//div[@id='%s']" % div_id)[0]

        return self.parse_details(detail_div)

    def leg_details(self, detail_url):
        div_id = 'ctl00_ContentPlaceHolder1_pageDetails'
        return self.details(detail_url, div_id)

    def action_details(self, detail_url):
        div_id = 'ctl00_ContentPlaceHolder1_pageTop1'
        return self.details(detail_url, div_id)

    def history(self, detail_url):
        detail_page = self.lxmlize(detail_url)

        try:
            history_table = detail_page.xpath(
                "//table[@id='ctl00_ContentPlaceHolder1_gridLegislation_ctl00']")[0]
        except IndexError:
            print(detail_url)
            raise

        history = [row[0] for row in self.parse_data_table(history_table)]

        try:
            history = sorted(history, key=self._action_sort_key)
        except (TypeError, ValueError):
            pass

        for action in history:
            yield action

    def _action_sort_key(self, action):
        action_date = self.to_date(action['Date'])
        action_url = action['Action\xa0Details']['url']

        return (action_date, action_url)

    def text(self, detail_url):
        detail_page = self.lxmlize(detail_url)

        text_div = detail_page.xpath(
            "//div[@id='ctl00_ContentPlaceHolder1_divText']")

        if len(text_div):
            return tostring(text_div[0], pretty_print=True).decode()
        else:
            return None

    def extract_votes(self, action_detail_url):
        action_detail_page = self.lxmlize(action_detail_url)
        try:
            vote_table = action_detail_page.xpath(
                "//table[@id='ctl00_ContentPlaceHolder1_gridVote_ctl00']")[0]
        except IndexError:
            self.warning("No votes found in table")
            return None, []
        votes = list(self.parse_data_table(vote_table))
        vote_list = []
        for vote, _, _ in votes:
            raw_option = vote['Vote'].lower()
            vote_list.append((self.VOTE_OPTIONS.get(raw_option, raw_option),
                              vote['Person Name']['label']))

        action_detail_div = action_detail_page.xpath(
            ".//div[@id='ctl00_ContentPlaceHolder1_pageTop1']")[0]
        action_details = self.parse_details(action_detail_div)
        result = action_details['Result'].lower()

        return result, vote_list


def date_within(created_after, created_before):
    payload = date_bound(created_after)

    payload['ctl00$ContentPlaceHolder1$txtFileCreated2'] =\
        '{d.year}-{d.month:02}-{d.day:02}'.format(d=created_before)
    payload['ctl00$ContentPlaceHolder1$txtFileCreated2$dateInput'] =\
        '{d.month}/{d.day}/{d.year}'.format(d=created_before)

    payload['ctl00_ContentPlaceHolder1_txtFileCreated2_dateInput_ClientState'] =\
        '{{"enabled":true, "emptyMessage":"","validationText":"{d.year}-{d.month:02}-{d.day:02}-00-00-00","valueAsString":"{d.year}-{d.month:02}-{d.day:02}-00-00-00","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00", "lastSetTextBoxValue":"{d.month}/{d.day}/{d.year}"}}'.format( # noqa : E501
            d=created_before)

    payload['ctl00$ContentPlaceHolder1$radFileCreated'] = 'between'

    return payload


def date_bound(creation_date):
    payload = {}

    payload['ctl00$ContentPlaceHolder1$txtFileCreated1'] =\
        '{d.year}-{d.month:02}-{d.day:02}'.format(d=creation_date)
    payload['ctl00$ContentPlaceHolder1$txtFileCreated1$dateInput'] =\
        '{d.month}/{d.day}/{d.year}'.format(d=creation_date)

    payload['ctl00_ContentPlaceHolder1_txtFileCreated1_dateInput_ClientState'] =\
        '{{"enabled":true, "emptyMessage":"","validationText":"{d.year}-{d.month:02}-{d.day:02}-00-00-00","valueAsString":"{d.year}-{d.month:02}-{d.day:02}-00-00-00","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00", "lastSetTextBoxValue":"{d.month}/{d.day}/{d.year}"}}'.format( # noqa : E501
            d=creation_date)

    return payload