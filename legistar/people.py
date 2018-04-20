from .base import LegistarScraper, LegistarAPIScraper


class LegistarPersonScraper(LegistarScraper):
    MEMBERLIST = None
    ALL_MEMBERS = None

    def councilMembers(self, extra_args=None, follow_links=True):
        payload = {}
        if extra_args:
            payload.update(extra_args)
            page = self.lxmlize(self.MEMBERLIST, payload)
            payload.update(self.sessionSecrets(page))

        if self.ALL_MEMBERS:
            payload['__EVENTTARGET'] = "ctl00$ContentPlaceHolder1$menuPeople"
            payload['__EVENTARGUMENT'] = self.ALL_MEMBERS

        for page in self.pages(self.MEMBERLIST, payload):
            table = page.xpath(
                "//table[@id='ctl00_ContentPlaceHolder1_gridPeople_ctl00']")[0]

            for councilman, headers, row in self.parseDataTable(table):
                if follow_links and type(councilman['Person Name']) == dict:

                    detail_url = councilman['Person Name']['url']
                    councilman_details = self.lxmlize(detail_url)
                    detail_div = councilman_details.xpath(
                        ".//div[@id='ctl00_ContentPlaceHolder1_pageDetails']")[0]

                    councilman.update(self.parseDetails(detail_div))

                    img = councilman_details.xpath(
                        "//img[@id='ctl00_ContentPlaceHolder1_imgPhoto']")
                    if img:
                        councilman['Photo'] = img[0].get('src')

                    committee_table = councilman_details.xpath(
                        "//table[@id='ctl00_ContentPlaceHolder1_gridDepartments_ctl00']")[0]
                    committees = self.parseDataTable(committee_table)

                    yield councilman, committees

                else:
                    yield councilman


class LegistarAPIPersonScraper(LegistarAPIScraper):
    date_format = '%Y-%m-%dT%H:%M:%S'

    def body_types(self):
        body_types_url = self.BASE_URL + '/bodytypes/'
        response = self.get(body_types_url)

        types = {body_type['BodyTypeName']: body_type['BodyTypeId']
                 for body_type in response.json()}

        return types

    def bodies(self):
        bodies_url = self.BASE_URL + '/bodies/'

        for body in self.pages(bodies_url, item_key="BodyId"):
            yield body

    def body_offices(self, body):
        body_id = body['BodyId']

        offices_url = (self.BASE_URL +
                       '/bodies/{}/OfficeRecords'.format(body_id))

        for office in self.pages(offices_url, item_key="OfficeRecordId"):
            yield office

    def toDate(self, text):
        return self.toTime(text).date()

    def person_sources_from_office(self, office):
        person_api_url = (self.BASE_URL +
                          '/persons/{OfficeRecordPersonId}'.format(**office))

        response = self.get(person_api_url)

        route = '/PersonDetail.aspx?ID={PersonId}&GUID={PersonGuid}'
        person_web_url = self.WEB_URL + route.format(**response.json())

        return person_api_url, person_web_url
