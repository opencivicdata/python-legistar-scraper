'''This module exports a single helper to serve as the get_organizations
callable on pupa jurisdictions.
'''
import pupa.scrape
from legistar.ext.pupa.scrapers import PupaGenerator


def generate_orgs(pupa_jurisdiction):
    '''This function generates orgs that can be inspected,
    mutated, etc, in the pupa Jurisdiction.get_organizations method.
    '''
    class OrgsGetter(PupaGenerator):
        '''This PupaGenerator subclass just provides a single overridden
        method to access the related Pupa jurisdiction object. Otherwise
        it's the same as any PupaGenerator.
        '''
        def get_jurisdiction(self):
            return self.inst

    orgs = OrgsGetter()
    orgs.set_instance(pupa_jurisdiction)

    get_orgs_from = orgs.get_legistar_scraper().cfg.GET_ORGS_FROM
    OrgsGetter.pupatypes = (get_orgs_from,)

    for org in orgs:
        if isinstance(org, pupa.scrape.Organization):
            yield org
    # yield from orgs.gen_pupatype_data()