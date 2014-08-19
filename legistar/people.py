import re
import urllib

import lxml.html

from pupa.scrape import Scraper, Person


class LegistarScraper(Scraper):

    def lxmlopen(self, url, payload=None):
        if payload:
            page = self.post(url, data=payload)
        else:
            page = self.get(url)
        doc = lxml.html.fromstring(page.text)
        doc.make_links_absolute(url)
        return doc

    def get_next_page(self, doc):
        payload = {}
        payload['__EVENTARGUMENT'] = ''
        payload['__VIEWSTATE'] = doc.xpath("//input[@name='__VIEWSTATE']/@value")[0]
        payload['__EVENTVALIDATION'] = doc.xpath("//input[@name='__EVENTVALIDATION']/@value")[0]
        pagejs = doc.xpath("//a[@class='rgCurrentPage']/following-sibling::a[1]/@href")
        if pagejs:
            payload['__EVENTTARGET'] = re.match(r'javascript:__doPostBack\(\'([\w\d\$]+)\',\'\'\)',
                                                pagejs[0]).groups()[0]
            url = urllib.parse.urljoin(self.jurisdiction.LEGISTAR_ROOT_URL, self.SEARCH_PAGE)
            return self.lxmlopen(url, payload)

    def parse_search_page(self, doc):
        RESULTS_TABLE_XPATH = '//table[contains(@class, "rgMaster")]'
        NO_RECORDS_FOUND_TEXT = ['No records were found', 'No records to display.']
        BAD_QUERY_TEXT = ['Please enter your search criteria.']

        tbl = doc.xpath(RESULTS_TABLE_XPATH)[0]

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

        next_page = self.get_next_page(doc)
        if next_page:
            yield from self.parse_search_page(next_page)


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
            if len(tds) == 1:
                self.warning('only one <td> for ' + label)
                continue
            content = tds[1].text_content().strip()
            # TODO: make sure mapping is complete
            item[self.DETAIL_PAGE_MAPPING[label]] = content

        item['sources'] = [url]

        return self.obj_from_dict(item)

    def obj_from_dict(self, item):
        raise NotImplementedError('obj_from_dict needs to be implemented in a subclass')

    def skip_item(self, item):
        return False

    def scrape(self):
        self.user_agent = 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1'
        
        url = urllib.parse.urljoin(self.jurisdiction.LEGISTAR_ROOT_URL, self.SEARCH_PAGE)
        doc = self.lxmlopen(url)
        for row in self.parse_search_page(doc):
            item = self.parse_search_row(row)
            if not self.skip_item(item):
                detail_url = self.get_detail_url(row)
                yield self.parse_detail_page(detail_url, item)


class LegistarPersonScraper(LegistarScraper):

    SEARCH_PAGE = 'People.aspx'
    SEARCH_ROW_MAPPING = {
        'Person Name': 'name',
        'Name': 'name',
        'Web Site': 'url',
        'Ward/Office': 'district',
        'E-mail': 'email',
        'Website': 'url',
        'Ward Office Phone': 'district_phone',
        'Ward Office Address': 'district_address',
        'City Hall Phone': 'city_hall_phone',
        'City Hall Address': 'city_hall_phone',
        'Fax': 'fax',
        'City': None,
        'State': None,
        'Zip': None,
    }
    DETAIL_PAGE_MAPPING = {
        'First name': 'first_name',
        'Last name': 'last_name',
        'E-mail': 'email',
        'Web site': 'url',
        'Website': 'url',
        'Notes': 'notes',
        'Ward Office Phone': 'district_phone',
        'Ward Office Fax': 'district_fax',
        'Ward Office Address': 'district_address',
        'City Hall Phone': 'city_hall_phone',
        'City Hall Fax': 'city_hall_fax',
        'City Hall Address': 'city_hall_phone',
        'City, state zip': None,
        'City, State Zip': None,
        '': None,
    }

    def obj_from_dict(self, item):
        district = item.pop('district', None)
        if district:
            district = district.lstrip('0')

        p = Person(name=item.pop('name'),
                   district=district,
                   primary_org=item.pop('primary_org', 'legislature'),
                   party=item.pop('party', None),
                   image=item.pop('image', ''),
                  )
        for contact in ('email', 'phone', 'address', 'fax'):
            if item.get('contact'):
                p.add_contact_detail(type=contact, value=item.pop(contact))

        if item.get('url'):
           p.add_link(item.pop('url'))

        if 'last_name' in item:
            p.sort_name = item.pop('last_name')

        for source in item.pop('sources'):
            p.add_source(source)

        # TODO: extras

        return p

    # unused
    CREATE_LEGISLATURE_MEMBERSHIP = False
    PPL_PARTY_REQUIRED = True

    PPL_DETAIL_TEXT_PHOTO = 'Photo'

    PPL_DETAIL_TABLE_TEXT_ORG = 'Department Name'
    PPL_DETAIL_TABLE_TEXT_ROLE = 'Title'
    PPL_DETAIL_TABLE_TEXT_START_DATE = 'Start Date'
    PPL_DETAIL_TABLE_TEXT_END_DATE = 'End Date'
    PPL_DETAIL_TABLE_TEXT_APPOINTED_BY = 'Appointed By'

    #TABS = {'events': 'Calendar.aspx', 'orgs': 'Departments.aspx', 'bills': 'Legislation.aspx',}
