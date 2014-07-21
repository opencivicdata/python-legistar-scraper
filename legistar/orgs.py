import re
import json
import collections
from datetime import datetime
from urllib.parse import urlparse, parse_qsl

from legistar.forms import Form
from legistar.tables import Table, TableRow
from legistar.views import SearchView, DetailView
from legistar.fields import FieldAggregator, make_item, gen_items
from legistar.base import CachedAttr, DictSetDefault, NoClobberDict


class OrgsFields(FieldAggregator):

    @make_item('name')
    def get_name(self):
        return self.get_field_text('name')

    @make_item('type')
    def get_type(self):
        return self.get_field_text('type')

    @make_item('meeting_location')
    def get_meeting_location(self):
        return self.get_field_text('meeting_location')

    @make_item('num_vacancies')
    def get_num_vacancies(self):
        return self.get_field_text('num_vacancies')

    @make_item('num_members')
    def get_num_members(self):
        return self.get_field_text('num_members')

    @make_item('sources', wrapwith=list)
    def gen_sources(self):
        grouped = collections.defaultdict(set)
        for note, url in self.chainmap['sources'].items():
            grouped[url].add(note)
        for url, notes in grouped.items():
            yield dict(url=url, note=', '.join(sorted(notes)))

    @make_item('identifiers', wrapwith=list)
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

    @make_item('notes')
    def get_district(self):
        return self.get_field_text('notes')


class OrgsDetailTable(Table):
    sources_note = 'organization detail table'


class OrgsDetailTableRow(TableRow):

    @make_item('org')
    def get_org(self):
        import pdb; pdb.set_trace()
        return self.get_field_text('org')


class OrgsDetailForm(Form):
    skip_first_submit = True
    sources_note = 'organization detail'