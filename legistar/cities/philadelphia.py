from pupa.scrape import Jurisdiction, Organization
from legistar.people import LegistarPersonScraper

'''
NOTE: Philadelphia's Legistar instance doesn't have people detail pages, so we can't get orgs
and memberships from a people scrape.

philadelphiacitycouncil.net is the place for that info
'''

class Philadelphia(Jurisdiction):
    timezone = 'America/New_York'
    division_id = 'ocd-division/country:us/state:pa/place:philadelphia'
    classification = 'government'
    name = 'Philadelphia'
    url = 'http://phila.gov'

    LEGISTAR_ROOT_URL = 'https://phila.legistar.com'
    scrapers = {}

    #def get_organizations(self):
    #    council = Organization('Philadelphia City Council', classification='legislature')
    #    for x in range(1,11):
    #        council.add_post(str(x), role='Council Member')
    #    council.add_post('At-Large', role='Council Member')
    #    yield council

    #BILL_DETAIL_TEXT_COMMITTEE = 'In control'
