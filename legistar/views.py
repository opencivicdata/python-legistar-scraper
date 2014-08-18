from urllib.parse import urljoin, urlparse

import lxml.html

from legistar.base import Base, CachedAttr
from legistar.fields import FieldAggregator
from legistar import detailpage
import legistar.jurisdictions.config
from legistar.jurisdictions.base import Config, JXN_CONFIGS


class View(Base):
    '''Base class for Legistar views. Pass in a config_obj and
    either url or parse lxml.html doc.

    Each view has an associated top-level FormClass and TableClass
    that are used to submit the View's form and extract information.
    Those related classes as specificed in the jurisdiction's
    legistar.jxn_config.Config object, or in the default Config object.
    '''

    def __init__(self, url=None, doc=None, **kwargs):
        # Setting doc to None forces the view to fetch the page.
        self.doc = doc
        # Allow the url to fall back to the parent chainmap url.
        if url is not None:
            self.chainmap['url'] = url
        self.kwargs = kwargs

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
        return self.cfg.views.get_by_pupatype(self.get_pupatype())

    @property
    def viewtype_meta(self):
        '''Return the viewtype metadata for this View based on its PUPATYPE
        and its VIEWTYPE, which is either 'search' or 'detail'.
        '''
        return getattr(self.viewmeta, self.get_viewtype())

    @property
    def Form(self):
        '''Return this view's form type. Note that it still needs to
        be invoked, and needs a reference back to its parent view so
        downstream code can access view-related meta data. There's a
        better way to do this, possibly with the same chained lookup
        code that other attrs use.
        '''
        return self.viewtype_meta.Form


class DetailView(View, FieldAggregator):

    @CachedAttr
    def field_data(self):
        visitor = self.make_child(detailpage.Visitor)
        return visitor.visit(self.doc)

    def asdict(self):
        data = dict(self)
        moredata = self._get_aggregator_func_data(data)
        data.update(moredata)
        return data


class LegistarScraper(View):

    _config_cache = {}

    events = meetings = get_events = gen_events
    bills = legislation = get_bills = gen_bills
    people = members = get_people = gen_people
    orgs = organizations = committees = get_orgs = gen_orgs

    def get_pupatype_searchview(self, pupatype, **kwargs):
        '''Where pupa model is one of 'bills', 'orgs', 'events'
        or 'people', return a matching View subclass.
        '''
        tabmeta = self.cfg.tabs.get_by_pupatype(pupatype)
        url = urljoin(self.cfg.root_url, tabmeta.path)
        view_meta = self.cfg.views.get_by_pupatype(pupatype)

        # Ability to pass doc via kwargs is helpful during testing.
        view = view_meta.search.View(url=url, **kwargs)
        view.inherit_chainmap_from(self.cfg)
        return view

    # ------------------------------------------------------------------------
    # These stricter scraper-getter functions are for pupa.
    # ------------------------------------------------------------------------
    @classmethod
    def get_config_strict(cls, division_id, classification, **kwargs):
        key = (division_id, classification)
        cache = cls._config_cache
        if key in cache:
            config_obj = cache[key]
            config_obj.kwargs = kwargs

        else:
            try:
                config_type = JXN_CONFIGS[key]
            except KeyError:
                msg = ("There doesn't appear to be a scraper defined for "
                       "jurisdiction %r yet.")
                raise ScraperNotFound(msg % key)
            config_obj = config_type(**kwargs)
            cache[key] = config_obj

        return config_obj

    @classmethod
    def get_scraper_strict(cls, division_id, classification, **kwargs):
        config_obj = cls.get_config_strict(division_id, classification, **kwargs)
        scraper = cls(**kwargs)
        scraper.set_parent_chainmap(config_obj.chainmap)
        return scraper
