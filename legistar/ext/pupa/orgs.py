import pupa.scrape

from legistar.ext.pupa.base import Adapter, Converter


class OrgsAdapter(Adapter):
    '''Converts legistar data into a pupa.scrape.Person instance.
    Note the make_item methods are popping values out the dict,
    because the associated keys aren't valid pupa.scrape.Person fields.
    '''
    pupa_model = pupa.scrape.Organization
    aliases = []
    extras_keys = ['meeting_location', 'num_members', 'num_vacancies']

    @make_item('classification')
    def get_classn(self):
        legistar_type = self.data.pop('type')
        return self.config.get_org_classification(legistar_type)


class OrgsConverter(Converter):
    '''Invokes the person and membership adapters to output pupa Person
    objects.
    '''
    adapter = OrgsAdapter

    def gen_agenda_items(self):
        yield from self.make_child(AgendaItemConverter, self.agenda)

    def __iter__(self):
        self.agenda = self.data.pop('agenda', [])
        yield self.get_adapter().get_instance()
        yield from self.gen_agenda_items()
