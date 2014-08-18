import re
import json
import collections
from datetime import datetime
from urllib.parse import urlparse, parse_qsl

import pupa.scrape

from legistar.forms import Form
from legistar.tables import Table, TableRow
from legistar.views import SearchView, DetailView
from legistar.fields import FieldAggregator, make_item, gen_items
from legistar.base import Adapter


class OrgsFields(FieldAggregator):

    def get_name(self):
        return self.get_field_text('name')

    def get_type(self):
        return self.get_field_text('type')

    def get_meeting_location(self):
        return self.get_field_text('meeting_location')

    def get_num_vacancies(self):
        return self.get_field_text('num_vacancies')

    def get_num_members(self):
        return self.get_field_text('num_members')

    def gen_sources(self):
        grouped = collections.defaultdict(set)
        for note, url in self.sources.items():
            grouped[url].add(note)
        for url, notes in grouped.items():
            yield dict(url=url, note=', '.join(sorted(notes)))

    #make_item('identifiers', wrapwith=list)
    def gen_identifiers(self):
        '''Yield out the internal legistar organization id and guid found
        in the detail page url.
        '''
        detail_url = self.get_field_url('name')
        url = urlparse(detail_url)
        for idtype, ident in parse_qsl(url.query):
            yield dict(
                scheme="legistar_" + idtype.lower(),
                identifier=ident)


class OrgsSearchView(SearchView):
    sources_note = 'Organizations search table'


class OrgsSearchTableRow(TableRow, OrgsFields):
    pass


class OrgsSearchTable(Table):
    sources_note = 'organizations search table'


class OrgsSearchForm(Form):
    '''Model the legistar orgs search form.
    '''
    skip_first_submit = True
    sources_note = 'organizations search table'

    def get_query(self, **kwargs):
        return dict(self.client.state, **kwargs)


class OrgsDetailView(DetailView, OrgsFields):
    sources_note = 'organization detail'

    def get_notes(self):
        return self.get_field_text('notes')


class OrgsDetailTable(Table):
    sources_note = 'organization detail table'


class OrgsDetailTableRow(TableRow):

    def get_org(self):
        return self.get_field_text('org')


class OrgsDetailForm(Form):
    skip_first_submit = True
    sources_note = 'organization detail'



class OrgsAdapter(Adapter):
    '''Converts legistar data into a pupa.scrape.Person instance.
    Note the make_item methods are popping values out the dict,
    because the associated keys aren't valid pupa.scrape.Person fields.
    '''
    pupa_model = pupa.scrape.Organization
    aliases = []
    extras_keys = [
        'meeting_location', 'num_members', 'num_vacancies', 'type']

    #make_item('classification')
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
