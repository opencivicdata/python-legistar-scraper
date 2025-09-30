from .base import LegistarAPIScraper


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

        offices_url = (self.BASE_URL
                       + '/bodies/{}/OfficeRecords'.format(body_id))

        for office in self.pages(offices_url, item_key="OfficeRecordId"):
            yield office

    def to_date(self, text):
        return self.to_time(text).date()

    def person_sources_from_office(self, office):
        person_api_url = (self.BASE_URL
                          + '/persons/{OfficeRecordPersonId}'.format(**office))

        response = self.get(person_api_url)

        route = '/PersonDetail.aspx?ID={PersonId}&GUID={PersonGuid}'
        person_web_url = self.WEB_URL + route.format(**response.json())

        return person_api_url, person_web_url
