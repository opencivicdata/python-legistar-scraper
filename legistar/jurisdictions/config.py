import re
import json

from legistar.jurisdictions.base import Config, make_item, overrides


class NYC(Config):
    '''Legistar config for New York City. Note that district, party,
    and bio are all combined into a `notes` field on legislator detail
    pages, so the custom functions below are necessary to extract those.
    '''
    TIMEZONE = 'America/New_York'

    nicknames = ['nyc']
    root_url = 'http://legistar.council.nyc.gov/'
    classification = 'government'
    division_id = 'ocd-division/country:us/state:ny/place:new_york'

    EVT_SEARCH_TABLE_TEXT_VIDEO = 'Multimedia'
    EVT_DETAIL_TEXT_VIDEO = 'Multimedia'
    EVT_DETAIL_TABLE_TEXT_VIDEO = 'Multimedia'

    # BILL_VOTE_OPTION_MAP = {
    #     'maternity': 'excused',
    #     }

    BILL_CLASSIFICATIONS = {
        'Introduction': 'bill',
        'Local Law': 'bill',
        'Resolution': 'resolution',
        }

    ORG_CLASSIFICATIONS = {
        'Land Use': 'committee',
        'Subcommittee': 'committee',
        'Task Force': 'commission',
        'Town Hall Meeting': 'commission',
    }

    # ------------------------------------------------------------------------
    # Methods to add specific fields onto person data.
    # ------------------------------------------------------------------------
    @make_item('person.district')
    def person_district(self, data):
        '''This corresponds to the label field on organizations posts.
        '''
        # First try to get it from bio.
        dist = re.findall(r'District\s+\d+', data['notes'])
        if dist:
            return dist.pop()

        # Then try website.
        dist = re.findall(r'/d(\d+)/', data['website'])
        if dist:
            return dist.pop()

        # Then email.
        dist = re.findall(r'd(\d+)', data['email'])
        if dist:
            return dist.pop()

    @make_item('person.party')
    def person_party(self, data):
        party = re.findall(r'Democrat|Republican', data['notes'], re.I)
        if party:
            party = party.pop()
            if party.startswith('Democrat'):
                party = 'Democratic'
            return party

    # ------------------------------------------------------------------------
    # Methods to add specific fields onto bill data.
    # ------------------------------------------------------------------------
    @make_item('bill.legislative_session')
    def bill_legislative_session(self, data):
        session = data['actions'][0]['date'].year
        return str(session)

    # ------------------------------------------------------------------------
    # Methods for customizing the pupa conversion process
    # ------------------------------------------------------------------------
    SPONSORSHIP_JUNK = (
        '(in conjunction with the Mayor)'
        )

    @overrides('BillsAdapter.should_drop_sponsor')
    def should_drop_sponsor(self, data):
        '''If this function retruns True, the sponsor obj is exluded from the
        sponsors list.
        '''
        return data['name'] in self.cfg.SPONSORSHIP_JUNK

    @overrides('BillsAdapter.gen_subjects')
    def gen_subjects(self):
        name = self.data['name'].strip()
        if name:
            yield name

    @overrides('VoteAdapter.get_vote_result')
    def get_vote_result(self, value):
        '''This might be uniform enough to push back into base config.
        '''
        if value == 'pass':
            return 'pass'
        else:
            return 'fail'

    @overrides('VoteAdapter.classify_motion_text')
    def classify_motion_text(self, motion_text):
        motion_text = motion_text.lower()
        if 'amended by' in motion_text:
            return ['passage:amendment']
        elif 'approved by council' in motion_text:
            return ['passage:bill']
        return []


class SanFrancisco(Config):
    nicknames = ['sf', 'frisco', 'thoms-home-town-sortof']
    root_url = 'https://sfgov.legistar.com'
    classification = 'government'
    division_id = 'ocd-division/country:us/state:ca/place:san_francisco'

    TIMEZONE = 'America/Los_Angeles'
    TOPLEVEL_ORG_MEMBERSHIP_TITLE_TEXT = 'Supervisor'
    TOPLEVEL_ORG_MEMBERSHIP_NAME_TEXT = 'Board of Supervisors'
    EVT_SEARCH_TABLE_TEXT_AUDIO = 'Audio'  # sfgov has this
    BILL_SEARCH_TABLE_TEXT_INTRO_DATE = 'Introduced'

    @make_item('person.district')
    def get_district(self, data):
        return self.DEFAULT_AT_LARGE_STRING

    @make_item('bill.legislative_session')
    def bill_legislative_session(self, data):
        if data['actions']:
            session = data['actions'][0]['date'].year
        else:
            import pdb; pdb.set_trace()
            session = data['on_agenda'].year
        return str(session)

    @overrides('VoteAdapter.get_vote_result')
    def get_vote_result(self, value):
        '''This might be uniform enough to push back into base config.
        '''
        if value.lower() == 'pass':
            return 'pass'
        else:
            return 'fail'


class Philadelphia(Config):
    '''XXX: Philadelphia's Legistar instance doesn't have people
    detail pages, so we can't get orgs and memberships from a people
    scrape. They also don't have org detail pages, so all we can
    get are org names, requiring a separate org scrape.
    '''
    TIMEZONE = 'America/New_York'
    nicknames = ['philly', 'pa']
    root_url = 'https://phila.legistar.com'
    division_id = 'ocd-division/country:us/state:pa/place:philadelphia'
    classification = 'government'

    # C'mon Philly, what's up with that.
    EVT_SEARCH_TABLE_DETAIL_AVAILABLE = False
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False
    BILL_DETAIL_TEXT_COMMITTEE = 'In control'

    @make_item('person.district')
    def get_district(self, data):
        return self.DEFAULT_AT_LARGE_STRING

    person_titles = ('Council President', 'Councilmember')

    @make_item('person.name')
    def person_name(self):
        rgx = '(%s)' % '|'.join(self.person_titles)
        import pdb; pdb.set_trace()
        return re.sub(rgx, '', )

    @overrides('OrgAdapter.should_drop_organization')
    def should_drop_organization(self, data):
        import pdb; pdb.set_trace()

    @make_item('bill.legislative_session')
    def bill_legislative_session(self, data):
        if data['actions']:
            session = data['actions'][0]['date'].year
        else:
            import pdb; pdb.set_trace()
            session = data['on_agenda'].year
        return str(session)


class Madison(Config):
    '''XXX: Something horribly wrong with people paginated results.
    Keep getting page 1 back.
    '''
    root_url = 'http://madison.legistar.com/'
    division_id = 'ocd-division/country:us/state:wi/place:madison'
    nicknames = ['madison']
    classification = 'government'
    TIMEZONE = 'America/Chicago'

    PPL_SEARCH_TABLE_TEXT_FULLNAME = 'Name'
    ORG_SEARCH_TABLE_TEXT_NAME = 'Boards, Commissions and Committees'
    ORG_CLASSIFICATIONS = {
        'ALLIED AREA TASK FORCE': 'commission',
        'TRANSPORT 2020 IMPLEMENTATION TASK FORCE': 'commission',
        'COMMON COUNCIL': 'legislature',
        'COMMON COUNCIL - DISCUSSION': 'commission',
        'COMMUNITY ACTION COALITION FOR SOUTH CENTRAL WISCONSIN INC': 'commission',
        'COMMUNITY DEVELOPMENT AUTHORITY': 'commission',
        'MADISON COMMUNITY FOUNDATION': 'commission',
        'MADISON FOOD POLICY COUNCIL': 'commission',
        'MADISON HOUSING AUTHORITY': 'commission',
        'PARKING COUNCIL FOR PEOPLE WITH DISABILITIES': 'commission',
    }
    @make_item('person.district')
    def person_district(self, data):
        '''This corresponds to the label field on organizations posts.
        '''
        # First try to get it from bio.
        dist = re.findall(r'District\s+\d+', data['notes'])
        if dist:
            return dist.pop()

        # Then try website.
        dist = re.findall(r'/district(\d+)/', data['website'])
        if dist:
            return dist.pop()

        # Then email.
        dist = re.findall(r'district(\d+)', data['email'])
        if dist:
            return dist.pop()

    @overrides('OrgsAdapter.get_classification')
    def orgs_get_classn(self):
        return self.cfg.get_org_classification(self.data['name'])


class JonesBoro(Config):
    '''XXX: on this one, top level org is not listed on people detail
    tables, so have to create it specially.
    '''
    nicknames = ['jonesboro']
    division_id = 'ocd-division/country:us/state:ar/place:jonesboro'
    root_url = 'http://jonesboro.legistar.com/'


class SolanoCounty(Config):
    '''Works with the defaults!
    '''
    nicknames = ['solano']
    root_url = 'https://solano.legistar.com'


class Chicago(Config):
    division_id = 'ocd-jurisdiction/country:us/state:il/place:chicago'
    nicknames = ['chicago', 'windy']
    root_url = 'https://chicago.legistar.com'
    PPL_DETAIL_TABLE_TEXT_ORG = 'Legislative Body'
    PPL_SEARCH_TABLE_TEXT_FULLNAME = 'Person Name'
    PPL_SEARCH_TABLE_TEXT_WEBSITE =  'Website'
    ORG_SEARCH_TABLE_TEXT_NAME = 'Legislative Body'

    BILL_SEARCH_TABLE_TEXT_FILE_NUMBER = 'Record #'
    BILL_DETAIL_TEXT_COMMITTEE = 'Current Controlling Legislative Body'

    @overrides('PersonAdapter.should_drop_person')
    def should_drop_person(self, data):
        import pdb; pdb.set_trace()


class MWRD(Config):
    division_id = 'ocd-division/country:us/state:il/sewer:mwrd'
    nicknames = ['mwrd']
    root_url = 'https://mwrd.legistar.com'


class BoroughofSitka(Config):
    '''Works with the defaults!
    '''
    nicknames = ['sitka']
    root_url = 'http://sitka.legistar.com/'


class Foley(Config):
    '''Works with the defaults!
    '''
    nicknames = ['foley']
    root_url = 'http://cityoffoley.legistar.com/'


class Maricopa(Config):
    '''XXX: Bill search Form doesn't work for Maricopa, for some reason.
    '''
    nicknames = ['maricopa']
    root_url = 'http://maricopa.legistar.com/'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False

    # @overrides('BillsSearchForm.get_extra_query')
    # def bills_get_extra_query(self):
    #     import pdb; pdb.set_trace()
    #     return {
    #         'ctl00_tabTop_ClientState': '{"selectedIndexes":["0"],"logEntries":[],"scrollState":{}}'
    #     }


class Mesa(Config):
    '''Works with the defaults!
    '''
    nicknames = ['mesa']
    root_url = 'http://mesa.legistar.com/'


class Rialto(Config):
    nicknames = ['rialto']
    root_url = 'http://rialto.legistar.com/'
    division_id = 'ocd-jurisdiction/country:us/state:az/place:rialto'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class Barrie(Config):
    nicknames = ['barrie']
    root_url = 'http://barrie.legistar.com/'
    division_id = 'ocd-division/country:ca/csd:3510045/place:barrie'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False
    ORG_CLASSIFICATIONS = {
        'Circulation List': 'committee',
        }


class LassenCounty(Config):
    '''Works with the defaults!
    '''
    nicknames = ['lassen']
    root_url = 'http://ramkumar.legistar.com/'


class LongBeach(Config):
    nicknames = ['longbeach']
    root_url = 'http://longbeach.legistar.com/'


class MontereyCounty(Config):
    verbose_name = "County of Monterey"
    nicknames = ['monterey']
    division_id = 'ocd-division/country:us/state:ca/county:monterey'
    root_url = 'http://monterey.legistar.com/'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class Oakland(Config):
    '''Has two org classifications that I can't figure out how
    to map to pupa org classifications: "Special Meeting" and "Requestor"
    '''
    nicknames = ['oakland']
    root_url = 'http://oakland.legistar.com/'
    division_id = 'ocd-division/country:us/state:ca/place:oakland'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class SanLeandro(Config):
    verbose_name = 'City of San Leoandro'
    nicknames = ['sl']
    root_url = 'http://sanleandro.legistar.com/'
    division_id = 'ocd-division/country:us/state:ca/place:san_leandro'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class SantaBarbaraCounty(Config):
    nicknames = ['sb']
    root_url = 'http://santabarbara.legistar.com/'
    division_id = 'ocd-division/country:us/state:ca/county:santa_barbara'


class CommerceCity(Config):
    nicknames = ['commerce']
    root_url = 'http://commerce.legistar.com/'


class CoralGables(Config):
    nicknames = []
    root_url = 'http://coralgables.legistar.com/'
    division_id = 'ocd-division/country:us/state:fl/place:coral_gables'


class Eustis(Config):
    nicknames = ['eustis']
    root_url = 'http://eustis.legistar.com/'


class FortLauderdale(Config):
    nicknames = ['fortl']
    root_url = 'http://fortlauderdale.legistar.com/'
    division_id = "ocd-division/country:us/state:fl/place:fort_lauderdale"


class KeyWest(Config):
    nicknames = ['keywest']
    root_url = 'http://keywest.legistar.com/'
    division_id = 'ocd-division/country:us/state:fl/place:key_west'


class SeminoleCounty(Config):
    nicknames = ['seminole']
    root_url = 'http://seminolecounty.legistar.com/'
    division_id = 'ocd-division/country:us/state:fl/county:seminole'


class PembrokePines(Config):
    nicknames = ['pp']
    root_url = 'http://ppines.legistar.com/'
    division_id = 'ocd-division/country:us/state:fl/place:pembroke_pines'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class Gainesville(Config):
    nicknames = ['gainesville']
    root_url = 'http://gainesville.legistar.com/'
    division_id = 'ocd-division/country:us/state:fl/place:gainesville'


class Canton(Config):
    nicknames = ['canton']
    root_url = 'http://canton.legistar.com/'
    division_id = 'ocd-division/country:us/state:ga/place:canton'


class Carrollton(Config):
    nicknames = ['carrolton']
    root_url = 'http://carrolltontx.legistar.com/'
    division_id = 'ocd-division/country:us/state:tx/place:carrollton'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class PowderSprings(Config):
    nicknames = ['powpow']
    root_url = 'http://powd.legistar.com/'
    division_id = 'ocd-division/country:us/state:ga/place:powder_springs'


class Lombard(Config):
    nicknames = ['lombard']
    root_url = 'http://lombard.legistar.com/'
    division_id = 'ocd-division/country:us/state:il/place:lombard'


class SedgwickCounty(Config):
    nicknames = ['sedgwick']
    root_url = 'http://sedgwickcounty.legistar.com/'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class RochesterHills(Config):
    nicknames = ['rhills']
    root_url = 'http://roch.legistar.com/'


class AnnArbor(Config):
    nicknames = ['annarbor']
    root_url = 'http://a2gov.legistar.com/'


class GrandRapids(Config):
    nicknames = ['grrr']
    root_url = 'http://grandrapids.legistar.com/'


class SaintPaul(Config):
    nicknames = ['saintpaul']
    root_url = 'http://stpaul.legistar.com/'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class Gulfport(Config):
    nicknames = ['gulf']
    root_url = 'http://gulfport.legistar.com/'


class Hattiesburg(Config):
    nicknames = ['hat']
    root_url = 'http://hattiesburg.legistar.com/'


class MecklenburgCounty(Config):
    nicknames = ['meck']
    root_url = 'http://mecklenburg.legistar.com/'


class Wilmington(Config):
    nicknames = ['wilm']
    root_url = 'http://wilmington.legistar.com/'


class HighPoint(Config):
    nicknames = ['hp']
    root_url = 'http://highpoint.legistar.com/'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class Newwark(Config):
    nicknames = ['newark']
    root_url = 'http://newark.legistar.com/'


class Albuquerque(Config):
    nicknames = ['albu']
    root_url = 'http://cabq.legistar.com/'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class LosAlamos(Config):
    nicknames = ['losalamos']
    root_url = 'http://losalamos.legistar.com/'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class Roswell(Config):
    nicknames = ['roswell']
    root_url = 'http://roswell.legistar.com/'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class Columbus(Config):
    nicknames = ['columbus']
    root_url = 'http://columbus.legistar.com/'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class Groveport(Config):
    nicknames = ['grove']
    root_url = 'http://groveport.legistar.com/'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class Milwaukee(Config):
    nicknames = ['mil']
    root_url = 'http://milwaukee.legistar.com/'


class MilwaukeeCounty(Config):
    nicknames = ['mil-co']
    root_url = 'http://milwaukeecounty.legistar.com/'


class Gahanna(Config):
    nicknames = ['gahanna']
    root_url = 'http://gahanna.legistar.com/'


class Norman(Config):
    nicknames = ['norman']
    root_url = 'http://norman.legistar.com/'


class Pittsburgh(Config):
    nicknames = ['pitt']
    root_url = 'http://pittsburgh.legistar.com/'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class RockHill(Config):
    nicknames = ['rock']
    root_url = 'http://rockhill.legistar.com/'


class Crossville(Config):
    nicknames = ['cross']
    root_url = 'http://crossvilletn.legistar.com/'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class Coppell(Config):
    nicknames = ['cop']
    root_url = 'http://coppell.legistar.com/'


class CorpusChristi(Config):
    nicknames = ['cc']
    root_url = 'http://corpuschristi.legistar.com/'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class LeagueCity(Config):
    nicknames = ['lc']
    root_url = 'http://leaguecity.legistar.com/'


class Mansfield(Config):
    nicknames = ['mans']
    root_url = 'http://mansfield.legistar.com/'


class McKinney(Config):
    nicknames = ['mckinney']
    root_url = 'http://mckinney.legistar.com/'


class Pflugerville(Config):
    nicknames = ['pf']
    root_url = 'http://pflugerville.legistar.com/'


class Alexandria(Config):
    nicknames = ['alex']
    root_url = 'http://alexandria.legistar.com/'
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = False


class Longview(Config):
    nicknames = ['longview']
    root_url = 'http://longview.legistar.com/'


class Olympia(Config):
    nicknames = ['olympia']
    root_url = 'http://olympia.legistar.com/'
