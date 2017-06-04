import datetime
import itertools
import traceback
from collections import defaultdict, deque
import re

from pupa.scrape import Scraper
import lxml.html
import lxml.etree as etree
import pytz

class LegistarScraper(Scraper):
    date_format='%m/%d/%Y'

    def __init__(self, *args, **kwargs) :
        super(LegistarScraper, self).__init__(*args, **kwargs)
        self.timeout = 600

    def lxmlize(self, url, payload=None):
        if payload :
            entry = self.post(url, payload, verify=False).text
        else :
            entry = self.get(url, verify=False).text
        page = lxml.html.fromstring(entry)
        page.make_links_absolute(url)
        return page

    def pages(self, url, payload=None) :
        page = self.lxmlize(url, payload)
        
        yield page

        next_page = page.xpath("//a[@class='rgCurrentPage']/following-sibling::a[1]")
        if payload and 'ctl00$ContentPlaceHolder1$btnSearch' in payload:
            del payload['ctl00$ContentPlaceHolder1$btnSearch']

        while len(next_page) > 0 :
            if payload is None:
                payload = {}
            
            payload.update(self.sessionSecrets(page))

            event_target = next_page[0].attrib['href'].split("'")[1]

            payload['__EVENTTARGET'] = event_target

            page = self.lxmlize(url, payload)

            yield page

            next_page = page.xpath("//a[@class='rgCurrentPage']/following-sibling::a[1]")


    def parseDetails(self, detail_div) :
        """
        Parse the data in the top section of a detail page.
        """
        detail_query = ".//*[starts-with(@id, 'ctl00_ContentPlaceHolder1_lbl')"\
                       "     or starts-with(@id, 'ctl00_ContentPlaceHolder1_hyp')]"
        fields = detail_div.xpath(detail_query)
        details = {}

        for field_key, field in itertools.groupby(fields, 
                                                  fieldKey) :
            field = list(field)
            field_1, field_2 = field[0], field[-1]
            key = field_1.text_content().replace(':', '').strip()
            if field_2.find('.//a') is not None :
                value = []
                for link in field_2.xpath('.//a') :
                    value.append({'label' : link.text_content().strip(),
                                  'url' : self._get_link_address(link)})
            elif 'href' in field_2.attrib :
                value = {'label' : field_2.text_content().strip(),
                         'url' : self._get_link_address(field_2)}
            else :
                value = field_2.text_content().strip()

            details[key] = value

        return details


    def parseDataTable(self, table):
        """
        Legistar uses the same kind of data table in a number of
        places. This will return a list of dictionaries using the
        table headers as keys.
        """
        headers = table.xpath(".//th[starts-with(@class, 'rgHeader')]")
        rows = table.xpath(".//tr[@class='rgRow' or @class='rgAltRow']")

        keys = []
        for header in headers :
            text_content = header.text_content().replace('&nbsp;', ' ').strip()
            if text_content :
                keys.append(text_content)
            else :
                keys.append(header.xpath('.//input')[0].value)

        for row in rows:
            try:
                data = defaultdict(lambda : None)

                for key, field in zip(keys, row.xpath("./td")):
                    text_content = self._stringify(field)

                    if field.find('.//a') is not None :
                        address = self._get_link_address(field.find('.//a'))
                        if address :
                            if key == '' and 'View.ashx?M=IC' in address:
                                key = 'iCalendar'
                                value = {'url': address}
                            else :
                                value = {'label': text_content, 
                                         'url': address}
                        else :
                            value = text_content
                    else :
                        value = text_content

                    data[key] = value

                yield data, keys, row

            except Exception as e:
                print('Problem parsing row:')
                print(etree.tostring(row))
                print(traceback.format_exc())
                raise e

    def _get_link_address(self, link):
        url = None
        if 'onclick' in link.attrib:
            onclick = link.attrib['onclick']
            if (onclick is not None 
                and onclick.startswith(("radopen('",
                                        "window.open",
                                        "OpenTelerikWindow"))):
                url = self.BASE_URL + onclick.split("'")[1]
        elif 'href' in link.attrib : 
            url = link.attrib['href']

        return url

    def _stringify(self, field) :
        for br in field.xpath("*//br"):
            br.tail = "\n" + br.tail if br.tail else "\n"
        for em in field.xpath("*//em"):
            if em.text :
                em.text = "--em--" + em.text + "--em--"
        return field.text_content().replace('&nbsp;', ' ').strip()

    def toTime(self, text) :
        time = datetime.datetime.strptime(text, self.date_format)
        time = pytz.timezone(self.TIMEZONE).localize(time)
        return time

    def toDate(self, text) :
        return self.toTime(text).date().isoformat()

    def now(self) :
        return datetime.datetime.utcnow().replace(tzinfo = pytz.utc)

    def mdY2Ymd(self, text) :
        month, day, year = text.split('/')
        return "%d-%02d-%02d" % (int(year), int(month), int(day))

    def sessionSecrets(self, page) :

        payload = {}
        payload['__EVENTARGUMENT'] = None
        payload['__VIEWSTATE'] = page.xpath("//input[@name='__VIEWSTATE']/@value")[0]
        try :
            payload['__EVENTVALIDATION'] = page.xpath("//input[@name='__EVENTVALIDATION']/@value")[0]
        except IndexError :
            pass

        return(payload)

def fieldKey(x) :
    field_id = x.attrib['id']
    field = re.split(r'hyp|lbl', field_id)[-1]
    field = field.split('Prompt')[0]
    field = field.rstrip('X21')
    return field

class LegistarAPIScraper(Scraper):
    date_format = '%Y-%m-%dT%H:%M:%S'
    
    def toTime(self, text) :
        time = datetime.datetime.strptime(text, self.date_format)
        time = pytz.timezone(self.TIMEZONE).localize(time)
        return time

    def pages(self, url, params=None, item_key=None):
        if params is None:
            params = {}
        
        seen = deque([], maxlen=1000)

        page_num = 0
        while page_num == 0 or len(response.json()) == 1000 :
            params['$skip'] = page_num * 1000
            response = self.get(url, params=params)

            for item in response.json() :
                if item[item_key] not in seen :
                    yield item
                    seen.append(item[item_key])

            page_num += 1





