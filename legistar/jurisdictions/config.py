import re

from legistar.jurisdictions.base import Config, make_item


class NYC(Config):
    nicknames = ['nyc', 'nyc']
    division_id = 'ocd-division/country:us/state:ny/place:new_york'
    root_url = 'http://legistar.council.nyc.gov/'

    @make_item('person.district')
    def person_district(self, data):
        # First try to get it from bio.
        dist = re.findall(r'District\s+(\d+)', data['notes'])
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
            return party.pop()

    @make_item('person.summary')
    def person_summary(self, data):
        '''The NYC person person bui follows the tilde in the
        district field on their detail pages.
        '''
        return data['notes']


class SanFrancisco(Config):
    nicknames = ['sf', 'frisco']
    division_id = 'ocd-division/country:us/state:ca/place:san_francisco'
    root_url = 'https://sfgov.legistar.com'


class Philadelphia(Config):
    nicknames = ['philly', 'pa']
    division_id = 'ocd-division/country:us/state:pa/place:philadelphia'
    EVT_DETAIL_AVAILABLE = False


class Madison(Config):
    nicknames = ['madison']
    root_url = 'http://madison.legistar.com/'
    PPL_TABLE_TEXT_FULLNAME = 'Name'


class JonesBoro(Config):
    nicknames = ['jonesboro']
    root_url = 'http://jonesboro.legistar.com/'


class Solano(Config):
    nicknames = ['solano']
    root_url = 'https://solano.legistar.com'


# ----------------
# Pasted
class BoroughofSitka(Config):
    nicknames = ['sitka']
    root_url = 'http://sitka.legistar.com/'


class Jonesboro(Config):
    nicknames = ['jonesboro']
    root_url = 'http://jonesboro.legistar.com/'


class Foley(Config):
    nicknames = ['foley']
    root_url = 'http://cityoffoley.legistar.com/'


class Maricopa(Config):
    nicknames = ['maricopa']
    root_url = 'http://maricopa.legistar.com/'


class Mesa(Config):
    nicknames = ['mesa']
    root_url = 'http://mesa.legistar.com/'


class Rialto(Config):
    nicknames = ['rialto']
    root_url = 'http://rialto.legistar.com/'


class Barrie(Config):
    nicknames = ['barrie']
    root_url = 'http://barrie.legistar.com/'


class LassenCounty(Config):
    nicknames = ['lassen']
    root_url = 'http://ramkumar.legistar.com/'


class LongBeach(Config):
    nicknames = []
    root_url = 'http://longbeach.legistar.com/'


class MontereyCounty(Config):
    nicknames = []
    root_url = 'http://monterey.legistar.com/'


class Oakland(Config):
    nicknames = []
    root_url = 'http://oakland.legistar.com/'


class SanFrancisco(Config):
    nicknames = []
    root_url = 'http://sfgov.legistar.com/'


class SanLeandro(Config):
    nicknames = []
    root_url = 'http://sanleandro.legistar.com/'


class SantaBarbaraCounty(Config):
    nicknames = ['sb']
    root_url = 'http://santabarbara.legistar.com/'


class SolanoCounty(Config):
    nicknames = []
    root_url = 'http://solano.legistar.com/'


class CommerceCity(Config):
    nicknames = []
    root_url = 'http://commerce.legistar.com/'


class CoralGables(Config):
    nicknames = []
    root_url = 'http://coralgables.legistar.com/'


class Eusticus(Config):
    nicknames = []
    root_url = 'http://eustis.legistar.com/'


class FortLauderdale(Config):
    nicknames = []
    root_url = 'http://fortlauderdale.legistar.com/'


class KeyWest(Config):
    nicknames = []
    root_url = 'http://keywest.legistar.com/'


class SeminoleCounty(Config):
    nicknames = []
    root_url = 'http://seminolecounty.legistar.com/'


class PembrokePines(Config):
    nicknames = ['pp']
    root_url = 'http://ppines.legistar.com/'


class Gainesville(Config):
    nicknames = []
    root_url = 'http://gainesville.legistar.com/'


class Canton(Config):
    nicknames = []
    root_url = 'http://canton.legistar.com/'


class Carrollton(Config):
    nicknames = []
    root_url = 'http://carrolltontx.legistar.com/'


class PowderSprings(Config):
    nicknames = []
    root_url = 'http://powd.legistar.com/'


class Chicago(Config):
    nicknames = []
    root_url = 'http://chicago.legistar.com/'


class Lombard(Config):
    nicknames = []
    root_url = 'http://lombard.legistar.com/'


class SedgwickCounty(Config):
    nicknames = []
    root_url = 'http://sedgwickcounty.legistar.com/'


class RochesterHills(Config):
    nicknames = []
    root_url = 'http://roch.legistar.com/'


class AnnArbor(Config):
    nicknames = []
    root_url = 'http://a2gov.legistar.com/'


class GrandRapids(Config):
    nicknames = []
    root_url = 'http://grandrapids.legistar.com/'


class SaintPaul(Config):
    nicknames = []
    root_url = 'http://stpaul.legistar.com/'


class Gulfport(Config):
    nicknames = []
    root_url = 'http://gulfport.legistar.com/'


class Hattiesburg(Config):
    nicknames = []
    root_url = 'http://hattiesburg.legistar.com/'


class MecklenburgCounty(Config):
    nicknames = []
    root_url = 'http://mecklenburg.legistar.com/'


class Wilmington(Config):
    nicknames = []
    root_url = 'http://wilmington.legistar.com/'


class HighPoint(Config):
    nicknames = []
    root_url = 'http://highpoint.legistar.com/'


class Newwark(Config):
    nicknames = []
    root_url = 'http://newark.legistar.com/'


class Albuquerque(Config):
    nicknames = []
    root_url = 'http://cabq.legistar.com/'


class LosAlamos(Config):
    nicknames = []
    root_url = 'http://losalamos.legistar.com/'


class Roswell(Config):
    nicknames = ['roswell']
    root_url = 'http://roswell.legistar.com/'


class Columbus(Config):
    nicknames = []
    root_url = 'http://columbus.legistar.com/'


class Groveport(Config):
    nicknames = []
    root_url = 'http://groveport.legistar.com/'


class Milwaukee(Config):
    nicknames = []
    root_url = 'http://milwaukee.legistar.com/'


class MilwaukeeCounty(Config):
    nicknames = []
    root_url = 'http://milwaukeecounty.legistar.com/'


class Gahanna(Config):
    nicknames = []
    root_url = 'http://gahanna.legistar.com/'


class Norman(Config):
    nicknames = []
    root_url = 'http://norman.legistar.com/'


class Philadelphia(Config):
    nicknames = []
    root_url = 'http://phila.legistar.com/'


class Pittsburgh(Config):
    nicknames = []
    root_url = 'http://pittsburgh.legistar.com/'


class RockHill(Config):
    nicknames = []
    root_url = 'http://rockhill.legistar.com/'


class Crossville(Config):
    nicknames = []
    root_url = 'http://crossvilletn.legistar.com/'


class Coppell(Config):
    nicknames = []
    root_url = 'http://coppell.legistar.com/'


class CorpusChristi(Config):
    nicknames = []
    root_url = 'http://corpuschristi.legistar.com/'


class LeagueCity(Config):
    nicknames = []
    root_url = 'http://leaguecity.legistar.com/'


class Mansfield(Config):
    nicknames = []
    root_url = 'http://mansfield.legistar.com/'


class McKinney(Config):
    nicknames = []
    root_url = 'http://mckinney.legistar.com/'


class Pflugerville(Config):
    nicknames = []
    root_url = 'http://pflugerville.legistar.com/'


class Alexandria(Config):
    nicknames = []
    root_url = 'http://alexandria.legistar.com/'


class Longview(Config):
    nicknames = []
    root_url = 'http://longview.legistar.com/'


class Olympia(Config):
    nicknames = []
    root_url = 'http://olympia.legistar.com/'




