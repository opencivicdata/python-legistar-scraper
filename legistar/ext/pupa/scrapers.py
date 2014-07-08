import pupa

from legistar.views import LegistarScraper
from legistar.ext.pupa.base import PupaExtBase
from legistar.ext.pupa.bills import BillsConverter
from legistar.ext.pupa.people import PeopleConverter
from legistar.ext.pupa.events import EventsConverter
from legistar.ext.pupa.orgs import OrgsConverter


class PupaGenerator(PupaExtBase):
    '''Instantiate this object with a list of pupatypes, then
    iterate over it to generate pupa objects. It invokes the
    legistar scraper and handles alias'ing the generic legistar
    field names over to valid pupa field names, then adds sources,
    links. etc.
    '''
    converter_types = dict(
        people=PeopleConverter,
        orgs=OrgsConverter,
        events=EventsConverter,
        bills=BillsConverter)

    def __init__(self, *pupatypes):
        self.pupatypes = pupatypes

    def __get__(self, inst, type_=None):
        self.inst = inst
        return self

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return self

    def __iter__(self):
        scraper = self.get_legistar_scraper()
        self.orgs = {}

        for pupatype in self.pupatypes:
            # Get the corresponding converter type.
            converter_type = self.converter_types[pupatype]
            for data in scraper.gen_pupatype_data(pupatype):
                # For each type, create a converter that inherits self's
                # chainmap.
                converter = self.make_child(converter_type, data)
                # And get the converted pupa instance.
                yield from converter

        # Yield out any accumulated objects.
        yield from self.orgs.values()

    def get_legistar_scraper(self):
        '''Get the owner instance's jurisdiction and retrieve the
        corresponding scraper. Inherit its chainmap.
        '''
        div_id = self.inst.jurisdiction.division_id
        classn = self.inst.jurisdiction.classification
        scraper = LegistarScraper.get_scraper_strict(
            division_id=div_id,
            classification=classn,
            # Pass in the pupa scraper as requests client.
            session=self.inst)

        # Inherit the jurisdiction's chainmap!
        scraper.config.provide_chainmap_to(self)
        # So children can access the generator.
        self.chainmap['generator'] = self

        return scraper


# ----------------------------------------------------------------------------
# Importables
# ----------------------------------------------------------------------------
class LegistarPeopleScraper(pupa.scrape.Scraper):
    # This also scrapes orgs.
    scrape = PupaGenerator('people')


class LegistarOrgsScraper(pupa.scrape.Scraper):
    scrape = PupaGenerator('orgs')


class LegistarEventsScraper(pupa.scrape.Scraper):
    scrape = PupaGenerator('events')


class LegistarBillsScraper(pupa.scrape.Scraper):
    scrape = PupaGenerator('bills')


if __name__ == '__main__':
    import sys
    import pprint
    class Dummy:
        division_id = 'nyc'
    class Scraper(LegistarBillsScraper):
        pass

    for token in Scraper(Dummy(), '.cache').scrape():
        pprint.pprint(token)
        import pdb; pdb.set_trace()