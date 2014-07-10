'''This module exports a single helper to serve as the get_organizations
callable on pupa jurisdictions.
'''
from legistar.ext.pupa.scrapers import PupaGenerator


class _OrgsGetter(PupaGenerator):
    def get_jurisdiction(self):
        return self.inst


def generate_orgs(pupa_jurisdiction):
    '''This function generates orgs that can be inspected,
    mutated, etc, in the pupa Jurisdiction.get_organizations method.
    '''
    orgs = _OrgsGetter('orgs')
    orgs.set_instance(pupa_jurisdiction)
    yield from orgs.gen_pupatype_data()