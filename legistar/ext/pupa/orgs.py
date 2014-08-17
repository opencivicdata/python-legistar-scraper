import pupa.scrape

from legistar.utils.itemgenerator import make_item
from legistar.ext.pupa.base import Adapter, Converter


class OrgsAdapter(Adapter):
    '''Converts legistar data into a pupa.scrape.Person instance.
    Note the make_item methods are popping values out the dict,
    because the associated keys aren't valid pupa.scrape.Person fields.
    '''
    pupa_model = pupa.scrape.Organization
    aliases = []
    extras_keys = [
        'meeting_location', 'num_members', 'num_vacancies', 'type']

    @make_item('classification')
    def _get_classification(self):
        return self.get_classification()

    def get_classification(self):
        legistar_type = self.data.pop('type')
        return self.config.get_org_classification(legistar_type)

    def should_drop_organization(self, data):
        '''If this function is overridden and returns true, matching orgs
        won't be emitted by the OrgsAdapter. Introduced specifically to
        handle the Philadelphia situation, where roles and potentially
        other weird data is listed on the jxn's org search page.
        '''
        return False

    def get_instance(self, **extra_instance_data):

        if self.should_drop_organization(self.data):
            return

        instance_data = self.get_instance_data()
        instance_data.update(extra_instance_data)

        extras = instance_data.pop('extras')
        sources = instance_data.pop('sources')
        identifiers = instance_data.pop('identifiers')

        instance = self.pupa_model(**instance_data)
        instance.extras.update(extras)
        for source in sources:
            instance.add_source(**source)
        for identifier in identifiers:
            instance.add_identifier(**identifier)

        return instance


class OrgsConverter(Converter):
    '''Invokes the person and membership adapters to output pupa Person
    objects.
    '''
    adapter = OrgsAdapter
