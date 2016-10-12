import datetime
import pytz

from .base import LegistarScraper
from pupa.scrape import Scraper

class LegistarPersonScraper(LegistarScraper):
    MEMBERLIST = None
    ALL_MEMBERS = None

    def councilMembers(self, follow_links=True) :

        if self.ALL_MEMBERS :
            page = self.lxmlize(self.MEMBERLIST)
            payload = {}
            payload['__EVENTTARGET'] = "ctl00$ContentPlaceHolder1$menuPeople"
            payload['__EVENTARGUMENT'] = self.ALL_MEMBERS
            

        for page in self.pages(self.MEMBERLIST, payload) :
            table = page.xpath(
                "//table[@id='ctl00_ContentPlaceHolder1_gridPeople_ctl00']")[0]

            for councilman, headers, row in self.parseDataTable(table):
                if follow_links and type(councilman['Person Name']) == dict:

                    detail_url = councilman['Person Name']['url']
                    councilman_details = self.lxmlize(detail_url)
                    detail_div = councilman_details.xpath(".//div[@id='ctl00_ContentPlaceHolder1_pageDetails']")[0]

                    councilman.update(self.parseDetails(detail_div))

                    img = councilman_details.xpath(
                        "//img[@id='ctl00_ContentPlaceHolder1_imgPhoto']")
                    if img :
                        councilman['Photo'] = img[0].get('src')

                    committee_table = councilman_details.xpath(
                        "//table[@id='ctl00_ContentPlaceHolder1_gridDepartments_ctl00']")[0]
                    committees = self.parseDataTable(committee_table)

                    yield councilman, committees

                else :
                    yield councilman

class LegistarAPIPersonScraper(Scraper):
    date_format = '%Y-%m-%dT%H:%M:%S'

    def body_types(self):
        body_types_url = self.BASE_URL + '/bodytypes/'
        response = self.get(body_types_url)

        types = {body_type['BodyTypeName'] : body_type['BodyTypeId']
                 for body_type in response.json()}

        return types

    def bodies(self):
        bodies_url = self.BASE_URL + '/bodies/'

        response = self.get(bodies_url)

        for body in response.json():
            yield body

    def body_offices(self, body):
        body_id = body['BodyId']

        offices_url = self.BASE_URL + '/bodies/{}/OfficeRecords'.format(body_id)

        page_num = 0
        params = {}
        while page_num == 0 or len(response.json()) == 1000 :
            params['$skip'] = page_num * 1000
            response = self.get(offices_url, params=params)

            for office in response.json() :
                yield office

            page_num += 1

    def toDate(self, text) :
        time = datetime.datetime.strptime(text, self.date_format)
        time = pytz.timezone(self.TIMEZONE).localize(time)
        return time.date()
            
