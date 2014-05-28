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
    def get_fullname(self):
        return self.get_field_text('name')

    @make_item('type')
    def get_fullname(self):
        return self.get_field_text('type')

    @make_item('sources', wrapwith=list)
    def gen_sources(self):
        grouped = collections.defaultdict(set)
        for note, url in self.chainmap['sources'].items():
            grouped[url].add(note)
        for url, notes in grouped.items():
            yield dict(url=url, note=', '.join(notes))


class OrgsSearchView(SearchView):
    sources_note = 'Organiations search'


class OrgsSearchTableRow(TableRow, OrgsFields):
    def get_detail_url(self):
        return self.get_field_url('fullname')


class OrgsSearchTable(Table):
    sources_note = 'organizations search table'


class OrgsSearchForm(Form):
    '''Model the legistar orgs search form.
    '''
    sources_note = 'organizations search'
    def get_query(self):
        return dict(self.client.state)


class OrgsDetailView(DetailView, OrgsFields):
    sources_note = 'organization detail'

    @make_item('notes')
    def get_district(self):
        return self.get_field_text('notes')

    @make_item('identifiers', wrapwith=list)
    def gen_identifiers(self):
        '''Yield out the internal legistar organization id and guid found
        in the detail page url.
        '''
        detail_url = self.chainmap['sources'][self.sources_note]
        url = urlparse(detail_url)
        for idtype, ident in parse_qsl(url.query):
            yield dict(
                scheme="legistar_" + idtype.lower(),
                identifier=ident)


class OrgsDetailTable(Table):
    sources_note = 'organization detail table'


class OrgsDetailTableRow(TableRow):

    @make_item('org')
    def get_org(self):
        return self.get_field_text('org')


class OrgsDetailForm(Form):
    skip_first_submit = True
    sources_note = 'organization detail'