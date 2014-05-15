from urllib.parse import urljoin, urlparse

import lxml.html
import visitors.ext.etree
import hercules import DictSetDefault

import legistar
from legistar.jxn_config import JXN_CONFIGS
from legistar import Base
from legistar.fields import FieldAggregator


class View(legistar.Base):
    '''Base class for Legistar views. Pass in a config_obj and
    either url or parse lxml.html doc.

    Each view has an associated top-level FormClass and TableClass
    that are used to submit the View's form and extract information.
    Those related classes as specificed in the jurisdiction's
    legistar.jxn_config.Config object, or in the default Config object.
    '''

    def __init__(self, url=None, doc=None):
        # Setting doc to None forces the view to fetch the page.
        self.chainmap['doc'] = doc

        # Allow the url to fall back to the parent chainmap url.
        if url is not None:
            self.chainmap['url'] = url

    # ------------------------------------------------------------------------
    # Managed attributes
    # ------------------------------------------------------------------------
    @property
    def sources_note(self):
        msg = 'Please set `sources_note` on this class: %r' % self.__class__
        raise NotImplementedError(msg)

    # ------------------------------------------------------------------------
    # Access to configable properties.
    # ------------------------------------------------------------------------
    @property
    def viewmeta(self):
        '''Return the view metadata for this View based on its PUPATYPE.
        '''
        return self.cfg.viewmeta.get_by_pupatype(self.PUPATYPE)

    @property
    def viewtype_meta(self):
        '''Return the viewtype metadata for this View based on its PUPATYPE
        and its VIEWTYPE, which is either 'search' or 'detail'.
        '''
        return getattr(self.viewmeta, self.VIEWTYPE)


class SearchView(View):

    def __iter__(self):
        '''Iterating over a search view generates tables of paginated search
        results.
        '''
        Form = self.viewtype_meta.Form
        yield from Form(self)


class DetailView(View, FieldAggregator):
    VIEWTYPE = 'detail'

    @CachedAttr
    def field_data(self):
        return DetailVisitor(self.cfg).visit(self.doc)

    def asdict(self):
        return dict(self)


class LegistarScraper(View):

    def gen_events(self):
        yield from self.yield_pupatype_objects('events')

    def gen_bills(self):
        yield from self.yield_pupatype_objects('bills')

    def gen_people(self):
        yield from self.yield_pupatype_objects('people')

    def gen_orgs(self):
        yield from self.yield_pupatype_objects('orgs')

    events = meetings = get_events = gen_events
    bills = legislation = get_bills = gen_bills
    people = members = get_people = gen_people
    orgs = organizations = committees = get_orgs = gen_orgs

    def get_pupatype_searchview(self, pupatype):
        '''Where pupa model is one of 'bills', 'orgs', 'events'
        or 'people', return a matching View subclass.
        '''
        tabmeta = self.cfg.tabs.get_by_pupatype(pupatype)
        url = urljoin(self.cfg.root_url, tabmeta.path)
        view_meta = self.cfg.viewmeta.get_by_pupatype(pupatype)
        view = view_meta.search.View(url=url)
        view.inherit_chainmap_from(self.cfg)
        return view

    def yield_pupatype_objects(self, pupatype):
        '''Given a pupa type, page through the search results and
        yield each object.
        '''
        yield from self.get_pupatype_searchview(pupatype)

    @classmethod
    def get_scraper(cls, url=None, ocd_id=None, **kwargs):
        '''Get the correct scraper by url or ocd_id.
        '''
        if url is not None:
            data = urlparse(url)
            try:
                config_type = JXN_CONFIGS[data.netloc]
            except KeyError:
                msg = ("There doesn't appear to be a scraper defined for "
                       "url %s yet.")
                raise ScraperNotFound(msg % url)
        elif ocd_id is not None:
            try:
                config_type = JXN_CONFIGS[ocd_id]
            except KeyError:
                msg = ("There doesn't appear to be a scraper defined for "
                       "jurisdiction %s yet.")
                raise ScraperNotFound(msg % ocd_id)
        else:
            raise Exception('Please supply the jurisdiction\'s url or ocd_id.')

        config_obj = config_type()
        scraper = cls(**kwargs)
        scraper.set_parent_chainmap(config_obj.chainmap)
        return scraper
