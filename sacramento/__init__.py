# encoding=utf-8
from pupa.scrape import Jurisdiction, Organization
from .people import SacramentoPersonScraper


class Sacramento(Jurisdiction):
    division_id = "ocd-division/country:us/state:ca/place:sacramento"
    classification = "legislature"
    name = "Sacramento City Council"
    url = "http://www.cityofsacramento.org/"
    scrapers = {
        "people": SacramentoPersonScraper,
    }

    legislative_sessions = []
    for year in range(2016, 2018):
        session = {"identifier": "{}".format(year),
                   "start_date": "{}-07-01".format(year),
                   "end_date": "{}-06-30".format(year + 1)}
        legislative_sessions.append(session)


    def get_organizations(self):
        org = Organization(name="Sacramento City Council", classification="legislature")

        org.add_post('Mayor of the City of Sacramento',
                     'Mayor',
                     division_id='ocd-division/country:us/state:ca/place:sacramento')

        for district in range(1, 9):
            org.add_post('Sacramento City Council Member, District {}'.format(district),
                         'Member',
                         division_id='ocd-division/country:us/state:ca/place:sacramento/council_district:{}'.format(district))

        yield org