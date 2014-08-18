import pupa

from legistar.views import LegistarScraper
from legistar.base import PupaExtBase
from legistar.bills import BillsConverter
from legistar.people import PeopleConverter
from legistar.events import EventsConverter
from legistar.orgs import OrgsConverter


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

    # Subclasses can set this attr, or callers can pass it in as an
    # __init__ arg.
    pupatypes = ()

    def __init__(self, *pupatypes, accumulate=False):
        # If this is true, the emitted objects all get held
        # in a list and yielded at the end, to give deduping a
        # chance to mutate them before the JSON gets get written out.
        self._accumulate = accumulate
        self._pupatypes = pupatypes

    def get_pupatypes(self):
        pupatypes = getattr(self, 'pupatypes', ())
        return set(pupatypes + self._pupatypes)

    def __get__(self, inst, type_=None):
        return self.set_instance(inst)

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return self

    def set_instance(self, instance):
        '''Where the PupaGenerator is not getattr's from the pupa Jurisdiction
        and the descriptor functionality is bypassed, this method sets the
        instance manually and gives the generator access to the jurisdiction.
        '''
        self.inst = instance
        return self

    def __iter__(self):
        yield from self.gen_pupatype_data()

    def gen_pupatype_data(self):
        scraper = self.get_legistar_scraper()

        cache = {}
        for pupatype in self.get_pupatypes():
            # Get the corresponding converter type.
            converter_type = self.converter_types[pupatype]
            for data in scraper.gen_pupatype_data(pupatype):
                # For each type, create a converter that inherits self's
                # chainmap.
                converter = self.make_child(converter_type, data)
                # And get the converted pupa instance.
                if self._accumulate:
                    for obj in converter:
                        if id(obj) not in cache:
                            cache[id(obj)] = obj
                else:
                    yield from converter

        if self._accumulate and cache:
            yield from cache.values()

    def get_jurisdiction(self):
        '''Return the jursdiction object. Overridden by LegistarOrgsGetter.
        '''
        return self.inst.jurisdiction

    def get_pupa_scraper(self):
        '''Get a pupa scraper to serve as the requests.session
        subtype used by the legistar scrapers.
        '''
        if isinstance(self.inst, pupa.scrape.Scraper):
            return self.inst
        scraper = pupa.scrape.Scraper(self.inst, '_cache')
        return scraper

    def get_legistar_scraper(self):
        '''Gets the owner instance's jurisdiction and retrieve the
        corresponding scraper. Inherits its chainmap.
        '''
        pupa_jxn = self.get_jurisdiction()
        div_id = pupa_jxn.division_id
        classn = pupa_jxn.classification
        scraper = LegistarScraper.get_scraper_strict(
            division_id=div_id,
            classification=classn,
            # Pass in the pupa scraper as requests client.
            session=self.get_pupa_scraper())

        # Inherit the jurisdiction's chainmap!
        scraper.config.pupa_jxn = pupa_jxn
        scraper.config.provide_chainmap_to(self)
        # So children can access the generator.
        self.chainmap['generator'] = self
        return scraper


class LegistarPeopleScraper(pupa.scrape.Scraper):
    # This also scrapes orgs.
    scrape = PupaGenerator('people')


class LegistarOrgsScraper(pupa.scrape.Scraper):
    scrape = PupaGenerator('orgs')


class LegistarEventsScraper(pupa.scrape.Scraper):
    scrape = PupaGenerator('events', accumulate=True)


class LegistarBillsScraper(pupa.scrape.Scraper):
    scrape = PupaGenerator('bills')
