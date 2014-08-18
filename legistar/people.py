import urllib

import lxml.html

from pupa.scrape import Scraper


class LegistarScraper(Scraper):

    def __init__(self, *args, **kwargs):
        super(LegistarScraper, self).__init__(*args, **kwargs)
        self._search_doc = None

    @property
    def search_doc(self):
        if not self._search_doc:
            url = urllib.parse.urljoin(self.jurisdiction.Config.ROOT_URL, self.SEARCH_PAGE)
            self._search_doc = self.lxmlopen(url)
        return self._search_doc

    def lxmlopen(self, url):
        page = self.get(url)
        doc = lxml.html.fromstring(page.text)
        doc.make_links_absolute(url)
        return doc

    def parse_search_page(self):
        RESULTS_TABLE_XPATH = '//table[contains(@class, "rgMaster")]'
        NO_RECORDS_FOUND_TEXT = ['No records were found', 'No records to display.']
        BAD_QUERY_TEXT = ['Please enter your search criteria.']

        tbl = self.search_doc.xpath(RESULTS_TABLE_XPATH)[0]

        headers = [th.text_content().replace('\xa0', ' ').strip()
                   for th in tbl.xpath('.//th[contains(@class, "rgHeader")]')]

        # get data
        for tr in tbl.xpath('.//tr')[1:]:
            # Skip the pagination rows.
            class_attr = tr.attrib.get('class', '')
            if ('rgPager' in class_attr or
                'rgFilterRow' in class_attr or
                tr.xpath('.//td[contains(@class, "rgPagerCell")]') or
                tr.xpath('.//th[@scope="col"]')
               ):
                continue

            for no_records_text in NO_RECORDS_FOUND_TEXT:
                if no_records_text in tr.text_content().strip():
                    msg = 'No records found in %r. Moving on.'
                    self.debug(msg % self)
                    raise StopIteration()

            for bad_query_text in BAD_QUERY_TEXT:
                if bad_query_text in tr.text_content().strip():
                    msg = ('Invalid query! This means the function that '
                           'determines the query data probably needs edits.')
                    self.critical(msg)
                    raise StopIteration()

            # get cells & wrap them up with the headers
            cells = tr.xpath('.//td')
            assert len(cells) == len(headers)

            yield list(zip(headers, cells))

    def convert_search_row(self, row):
        result = {}
        for name, td in row:
            result[self.SEARCH_ROW_MAPPING[name]] = td.text_content()

    def get_detail_url(self, row):
        return row[0][1].xpath('.//a/@href')[0]

    def parse_detail_page(self, url, table_bits):
        doc = self.lxmlopen(url)

    def scrape(self):
        for row in self.parse_search_page():
            table_bits = self.convert_search_row(row)
            detail_url = self.get_detail_url(row)
            self.parse_detail_page(detail_url, table_bits)


class LegistarPersonScraper(LegistarScraper):

    SEARCH_PAGE = 'People.aspx'
    SEARCH_ROW_MAPPING = {'Person Name': 'name',
                          'Web Site': 'url'}

    # unused
    CREATE_LEGISLATURE_MEMBERSHIP = False
    PPL_PARTY_REQUIRED = True

    # People search config.
    PPL_SEARCH_TABLE_TEXT_EMAIL =  'E-mail'
    PPL_SEARCH_TABLE_TEXT_FAX = 'Fax'
    PPL_SEARCH_TABLE_TEXT_DISTRICT = 'Ward/Office'
    PPL_SEARCH_TABLE_TEXT_DISTRICT_PHONE = 'Ward Office Phone'
    PPL_SEARCH_TABLE_TEXT_DISTRICT_ADDRESS = 'Ward Office Address'
    PPL_SEARCH_TABLE_TEXT_DISTRICT_ADDRESS_STATE = ('State', 0)
    PPL_SEARCH_TABLE_TEXT_DISTRICT_ADDRESS_CITY = ('City', 0)
    PPL_SEARCH_TABLE_TEXT_DISTRICT_ADDRESS_ZIP = ('Zip', 0)
    PPL_SEARCH_TABLE_TEXT_CITYHALL_PHONE = 'City Hall Phone'
    PPL_SEARCH_TABLE_TEXT_CITYHALL_ADDRESS = 'City Hall Address'
    PPL_SEARCH_TABLE_TEXT_CITYHALL_ADDRESS_STATE = ('State', 1)
    PPL_SEARCH_TABLE_TEXT_CITYHALL_ADDRESS_CITY = ('City', 1)
    PPL_SEARCH_TABLE_TEXT_CITYHALL_ADDRESS_ZIP = ('Zip', 1)

    # Whether people detail pages are available.
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = True
    # Nonsense to prevent detail queries on detail pages.
    PPL_DETAIL_TABLE_DETAIL_AVAILABLE = False

    PPL_DETAIL_TEXT_FIRSTNAME = 'First name'
    PPL_DETAIL_TEXT_LASTNAME = 'Last name'
    PPL_DETAIL_TEXT_WEBSITE =  'Web site'
    PPL_DETAIL_TEXT_EMAIL = 'E-mail'
    PPL_DETAIL_TEXT_NOTES = 'Notes'

    # This field actually has no label, but this pretends it does,
    # so as to support the same interface.
    PPL_DETAIL_TEXT_PHOTO = 'Photo'

    # The string to indicate that person's rep'n is "at-large".
    DEFAULT_AT_LARGE_STRING = 'At-Large'
    # The string indicating person's membership in the council, for example.
    # This is usually the first row in the person detail chamber.
    # It's the string value of the first PPL_MEMB_TABLE_TEXT_ROLE
    TOPLEVEL_ORG_MEMBERSHIP_TITLE = 'Council Member'
    TOPLEVEL_ORG_MEMBERSHIP_NAME = 'City Council'

    PPL_DETAIL_TABLE_TEXT_ORG = 'Department Name'
    PPL_DETAIL_TABLE_TEXT_ROLE = 'Title'
    PPL_DETAIL_TABLE_TEXT_START_DATE = 'Start Date'
    PPL_DETAIL_TABLE_TEXT_END_DATE = 'End Date'
    PPL_DETAIL_TABLE_TEXT_APPOINTED_BY = 'Appointed By'
    #TABS = {'events': 'Calendar.aspx', 'orgs': 'Departments.aspx', 'bills': 'Legislation.aspx',}
