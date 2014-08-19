import urllib

import lxml.html

from pupa.scrape import Scraper, Person


class LegistarScraper(Scraper):

    def __init__(self, *args, **kwargs):
        super(LegistarScraper, self).__init__(*args, **kwargs)
        self._search_doc = None

    @property
    def search_doc(self):
        if not self._search_doc:
            url = urllib.parse.urljoin(self.jurisdiction.LEGISTAR_ROOT_URL, self.SEARCH_PAGE)
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

    def parse_search_row(self, row):
        result = {}
        for name, td in row:
            # TODO: make sure mapping is complete
            result[self.SEARCH_ROW_MAPPING[name]] = td.text_content().strip()
        return result

    def get_detail_url(self, row):
        return row[0][1].xpath('.//a/@href')[0]

    def parse_detail_page(self, url, item):
        doc = self.lxmlopen(url)
        tbl = doc.xpath('//table[@id="ctl00_ContentPlaceHolder1_tblMain"]')[0]
        for tr in tbl.xpath('.//tr'):
            tds = tr.xpath('td')
            label = tds[0].text_content().strip().strip(':')
            content = tds[1].text_content().strip()
            # TODO: make sure mapping is complete
            item[self.DETAIL_PAGE_MAPPING[label]] = content

        item['sources'] = [url]

        return self.obj_from_dict(item)

    def obj_from_dict(self, item):
        raise NotImplementedError('obj_from_dict needs to be implemented in a subclass')

    def scrape(self):
        for row in self.parse_search_page():
            item = self.parse_search_row(row)
            detail_url = self.get_detail_url(row)
            yield self.parse_detail_page(detail_url, item)


class LegistarPersonScraper(LegistarScraper):

    SEARCH_PAGE = 'People.aspx'
    SEARCH_ROW_MAPPING = {
        'Person Name': 'name',
        'Web Site': 'url'
    }
    DETAIL_PAGE_MAPPING = {
        'First name': 'first_name',
        'Last name': 'last_name',
        'E-mail': 'email',
        'Web site': 'url',
        'Notes': 'notes',
    }

    def obj_from_dict(self, item):
        p = Person(name=item.pop('name'),
                   district=item.pop('district'),
                   party=item.pop('party'),
                   primary_org='legislature',
                   image=item.pop('image', ''),
                  )
        for contact in ('email', 'phone', 'address', 'fax'):
            if item.get('contact'):
                p.add_contact_detail(type=contact, value=item.pop(contact))

        if 'url' in item:
           p.add_link(item.pop('url'))

        if 'last_name' in item:
            p.sort_name = item.pop('last_name')

        for source in item.pop('sources'):
            p.add_source(source)

        # extras

        return p

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

    PPL_DETAIL_TEXT_PHOTO = 'Photo'

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
