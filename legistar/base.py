import re
import urllib
import lxml.html
from pupa.scrape import Scraper

class LegistarScraper(Scraper):

    RESULTS_TABLE_XPATH = '//table[contains(@class, "rgMaster")]'
    NO_RECORDS_FOUND_TEXT = ['No records were found', 'No records to display.']
    BAD_QUERY_TEXT = ['Please enter your search criteria.']
    EXTRA_FIELDS = ()
    DROP_FIELDS = ()

    def lxmlopen(self, url, payload=None):
        """ use scrapelib to open a file and get a normalized lxml.html doc from it """
        if payload:
            page = self.post(url, data=payload)
        else:
            page = self.get(url)
        doc = lxml.html.fromstring(page.text)
        doc.make_links_absolute(url)
        return doc

    def get_next_page(self, doc):
        """ mimic the __doPostBack js """
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
        """
            get all result rows from search and yield them out as lists of tuples
            [(header, value), (header2, value2), etc.]

            transparently takes care of pagination within the function
        """
        tbl = doc.xpath(self.RESULTS_TABLE_XPATH)[0]

        headers = [th.text_content().replace('\xa0', ' ').strip()
                   for th in tbl.xpath('.//th[contains(@class, "rgHeader")]')]

        for tr in tbl.xpath('.//tr')[1:]:

            # Skip the pagination & non-data rows.
            class_attr = tr.attrib.get('class', '')
            if ('rgPager' in class_attr or
                'rgFilterRow' in class_attr or
                tr.xpath('.//td[contains(@class, "rgPagerCell")]') or
                tr.xpath('.//th[@scope="col"]')
               ):
                continue

            for no_records_text in self.NO_RECORDS_FOUND_TEXT:
                if no_records_text in tr.text_content().strip():
                    self.debug('No records found, moving on.')
                    raise StopIteration()

            for bad_query_text in self.BAD_QUERY_TEXT:
                if bad_query_text in tr.text_content().strip():
                    self.critical('Invalid query!')
                    raise StopIteration()

            # get cells & wrap them up with the headers
            cells = tr.xpath('.//td')
            assert len(cells) == len(headers)
            yield list(zip(headers, cells))

        # after rows are depleted, check if there is another page and recurse
        next_page = self.get_next_page(doc)
        if next_page:
            yield from self.parse_search_page(next_page)

    def extract_content_to_item(self, item, name, element, mapping):
        """
            use a mapping to extract data from element into ``item``

            potential enhancements: add filters other than strip
        """
        mapval = mapping[name]
        if mapval is not None:
            item[mapval] = element.text_content().strip()

    def parse_search_row(self, row):
        """
            use self.SEARCH_ROW_MAPPING to convert <th> text to expected variable names 

            instead of overriding this function you can modify SEARCH_ROW_MAPPING
        """
        result = {}
        for name, td in row:
            self.extract_content_to_item(result, name, td, self.SEARCH_ROW_MAPPING)
        return result

    def parse_detail_page(self, url, item):
        """
            pull the rows out of the tblMain detail page

            instead of overriding this function you can modify DETAIL_PAGE_MAPPING
        """
        doc = self.lxmlopen(url)
        tbl = doc.xpath('//table[@id="ctl00_ContentPlaceHolder1_tblMain"]')[0]
        for tr in tbl.xpath('.//tr'):
            tds = tr.xpath('td')
            label = tds[0].text_content().strip().strip(':')
            if len(tds) == 1:
                self.warning('only one <td> for ' + label)
                continue
            self.extract_content_to_item(item, label, tds[1], self.DETAIL_PAGE_MAPPING)

        return self.obj_from_dict(item)

    def get_detail_url(self, row):
        """
            get the URL to the row's detail page
            (overriding is recommended if the usual pattern doesn't hold)
        """
        return row[0][1].xpath('.//a/@href')[0]

    def obj_from_dict(self, item):
        """
            implemented in each subclass and recommended hook for overriding the conversion
            from collected data to a dict
        """
        raise NotImplementedError('obj_from_dict needs to be implemented in a subclass')

    def skip_item(self, item):
        """ can be overridden with custom logic to skip unruly items """
        return False

    def scrape(self):
        # seems to help w/ aspx stuff?
        self.user_agent = ('Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 '
                           'Fedora/3.0.1-1.fc9 Firefox/3.0.1')
        # get first page
        url = urllib.parse.urljoin(self.jurisdiction.LEGISTAR_ROOT_URL, self.SEARCH_PAGE)
        doc = self.lxmlopen(url)

        for row in self.parse_search_page(doc):
            item = self.parse_search_row(row)
            item['sources'] = [url]
            if not self.skip_item(item):
                detail_url = self.get_detail_url(row)
                item['sources'].append(detail_url)
                yield self.parse_detail_page(detail_url, item)
