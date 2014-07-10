'''This module exports a single helper to serve as the get_organizations
callable on pupa jurisdictions.
'''
from legistar.ext.pupa.scrapers import PupaGenerator


class _OrgsGetter(PupaGenerator):
    '''This PupaGenerator subclass just provides a single overridden
    method to access the related Pupa jurisdiction object. Otherwise
    it's the same as any PupaGenerator.
    '''
    pupatypes = ('orgs',)
    def get_jurisdiction(self):
        return self.inst


def generate_orgs(pupa_jurisdiction):
    '''This function generates orgs that can be inspected,
    mutated, etc, in the pupa Jurisdiction.get_organizations method.
    '''
    orgs = _OrgsGetter()
    orgs.set_instance(pupa_jurisdiction)
    yield from orgs.gen_pupatype_data()