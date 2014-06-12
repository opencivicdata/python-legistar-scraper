import re
import json
import collections
from datetime import datetime

from legistar.forms import Form
from legistar.tables import Table, TableRow
from legistar.views import SearchView, DetailView
from legistar.fields import FieldAggregator, make_item, gen_items
from legistar.fields import ElementAccessor
from legistar.base import DictSetDefault, NoClobberDict

# https://github.com/guelo/legistar-scrape/compare/fgregg:master...master

class BillsFields(FieldAggregator):

    text_fields = (
        'file_number', 'law_number', 'type', 'status',
        'final_action', 'title', 'name', 'version')

    @make_item('sources', wrapwith=list)
    def gen_sources(self):
        grouped = collections.defaultdict(set)
        for note, url in self.chainmap['sources'].items():
            grouped[url].add(note)
        for url, notes in grouped.items():
            yield dict(url=url, note=', '.join(sorted(notes)))


class BillsSearchView(SearchView):
    sources_note = 'bills search'


class BillsSearchTableRow(TableRow, BillsFields):

    def get_detail_url(self):
        return self.get_field_url('details')
    @make_item('location')

    def get_location(self):
        import pdb; pdb.set_trace()
        return self.get_field_text('location')


class BillsSearchTable(Table):
    sources_note = 'bills search table'


class BillsSearchForm(Form):
    '''Model the legistar "Calendar" search form.
    '''
    sources_note = 'bills search table'

    def get_query(self, time_period=None, bodies=None):
        configval = self.get_config_value
        time_period = time_period or configval('time_period')
        bodies = bodies or configval('types')
        clientstate = json.dumps({'value': time_period})

        query = {
            configval('types_el_name'): bodies,
            configval('time_period_el_name'): time_period,
            configval('clientstate_el_name'): clientstate,
            }
        self.debug('Query is %r' % query)
        query = dict(self.client.state, **query)
        return query


class BillsDetailView(DetailView, BillsFields):
    sources_note = 'bill detail'

    @make_item('agenda', wrapwith=list)
    def gen_agenda(self):
        yield from self.Form(self)


class BillsDetailTable(Table):
    sources_note = 'bill detail table'


class BillsDetailTableRow(TableRow):

    def _get_type(self):
        typetext = self.get_field_text('type')
        if typetext is not None:
            typetext = typetext.lower()
        return self.typetext_map.get(typetext, 'document')

    @make_item('version')
    def get_version(self):
        return self.get_field_text('version')


class BillsDetailForm(Form):
    sources_note = 'bill detail'