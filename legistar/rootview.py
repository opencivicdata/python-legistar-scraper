from urllib.parse import urljoin, urlparse

from legistar.jxn_config import JXN_CONFIGS
from legistar.base.view import View


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
        view.inherit_ctx_from(self.cfg)
        return view

    def yield_pupatype_objects(self, pupatype):
        '''Given a pupa type, page through the search results and
        yield each object.
        '''
        yield from self.get_pupatype_searchview(pupatype)


def get_scraper(*args, **kwargs):
    '''Get the correct scraper by url or ocd_id.
    '''
    url = kwargs.pop('url')
    ocd_id = kwargs.pop('ocd_id')

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
    scraper = LegistarScraper(*args, **kwargs))
    scraper.set_parent_ctx(config_obj.ctx)
    return scraper
