'''This module exports a single helper to serve as the get_organizations
callable on pupa jurisdictions.
'''
from legistar.ext.pupa.base import PupaExtBase
from legistar.ext.pupa.scrapers import LegistarOrgsScraper


class LegistarOrgsGetter(PupaExtBase):

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __get__(self, inst, type_=None):
        self.inst = inst
        return self

    def __call__(self):
        '''Per pupa.scrape.jurisdiction.JurisdictionScraper, the get_organizations
        function takes no arguments.
        '''
        return self

    def __iter__(self):
        for org in self.make_child(LegistarOrgsScraper):
            import pdb; pdb.set_trace()