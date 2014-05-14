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

    events = meetings = gen_events
    bills = legislation = gen_bills
    people = members = gen_people
    orgs = organizations = committees = gen_orgs

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
        for page in self.get_pupatype_searchview(pupatype):
            yield from page


def get_scraper(url=None, ocd_id=None):
    if url is not None:
        data = urlparse(url)
        config_type = JXN_CONFIGS[data.netloc]
    elif ocd_id is not None:
        config_type = JXN_CONFIGS[ocd_id]
    else:
        raise Exception('Please supply the jurisdiction\'s url or ocd_id.')

    config_obj = config_type()
    scraper = LegistarScraper()
    scraper.set_parent_ctx(config_obj.ctx)
    return scraper
