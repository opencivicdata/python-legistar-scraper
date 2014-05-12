from urllib.parse import urljoin

from legistar.base.view import View


class Root(View):
    '''Here we don't know what the view is.
    '''
    def get_current_tabmeta(self):
        '''Inspect the nav tabs to get metadata for the current tab.
        '''
        current_tab = self.get_active_tab()
        tabmeta = self.cfg.tabs.by_text(current_tab['text'])
        return tabmeta

    def get_current_pupatype(self):
        '''Inspect the current page to determine what pupa type is displayed.
        '''
        tabmeta = self.get_current_tabmeta()
        return tabmeta.pupatype

    def get_pupatype_viewmeta(self, pupatype):
        '''Get the View subclass defined for each pupa type.
        '''
        return self.cfg.viewmeta.get_by_pupatype(pupatype)

    def get_pupatype_view(self, pupatype):
        '''Where pupa model is one of 'bills', 'orgs', 'events'
        or 'people', return a matching View subclass.
        '''
        tabmeta = self.cfg.tabs.get_by_pupatype(pupatype)
        url = urljoin(self.cfg.root_url, tabmeta.path)
        view_meta = self.get_pupatype_viewmeta(pupatype)
        return view view_meta.search.View(self.cfg, url=url)


    def yield_pupatype_objects(self, pupatype):
        '''Given a pupa type, page through the search results and
        yield each object.
        '''
        for page in self.get_pupatype_view(pupatype):
            yield from page

    # Generators for each specific pupa type.
    def gen_events(self):
        yield from self.yield_pupatype_objects('events')

    def gen_bills(self):
        yield from self.yield_pupatype_objects('bills')

    def gen_people(self):
        yield from self.yield_pupatype_objects('people')

    def gen_orgs(self):
        yield from self.yield_pupatype_objects('orgs')
