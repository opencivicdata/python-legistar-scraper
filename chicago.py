from pupa.scrape import Jurisdiction, Organization
from legistar.people import LegistarPersonScraper
from legistar.config import Config


class ChicagoPersonScraper(LegistarPersonScraper):
    def obj_from_dict(self, item):
        if item['district'] == 'Mayor':
            item['primary_org'] = 'executive'
        return super(ChicagoPersonScraper, self).obj_from_dict(item)


class Chicago(Jurisdiction):
    classification = 'government'
    division_id = 'ocd-division/country:us/state:il/place:chicago'
    name = 'Chicago'
    timezone = 'America/Chicago'
    url = 'http://cityofchicago.org'

    parties = [
        {'name': 'Democratic'},
        {'name': 'Republican'}
    ]
    scrapers = {'people': ChicagoPersonScraper}

    LEGISTAR_ROOT_URL = 'https://chicago.legistar.com'

    def get_organizations(self):
        council = Organization('Chicago City Council', classification='legislature')
        for x in range(1,51):
            council.add_post(str(x), role='Alderman')
        council.add_post('Clerk', role='Clerk')
        yield council

        executive = Organization('Chicago Executive Branch', classification='executive')
        executive.add_post('Mayor', role='Mayor')
        yield executive

    #class Config(Config):
    #    ORG_SEARCH_TABLE_TEXT_NAME = 'Legislative Body'
    #    BILL_SEARCH_TABLE_TEXT_FILE_NUMBER = 'Record #'
    #    BILL_DETAIL_TEXT_COMMITTEE = 'Current Controlling Legislative Body'

    #    def orgs_get_classn(self):
    #        return self.cfg.get_org_classification(self.data['name'])

    #    def should_drop_organization(self, data):
    #        # Skip phone orgs like "Office of the Mayor"
    #        return data['name'].lower().startswith('office of')

    #    def should_drop_bill(self, data):
    #        '''The chicago legistar site has type error where two bills in the
    #        same session have the same id. One is just to approve a handicapped
    #        parking permit. This drops it.
    #        '''
    #        drop_guids = [
    #            'B99F2EAD-A0CF-44FA-899D-1AC5D8A561C7'
    #            ]
    #        for identifier in data['identifiers']:
    #            if identifier['scheme'] == 'legistar_guid':
    #                if identifier['identifier'] in drop_guids:
    #                    return True
    #        return False
