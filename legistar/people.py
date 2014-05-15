import re
import json
import collections
from datetime import datetime

from legistar.forms import Form
from legistar.tables import Table, TableRow
from legistar.views import SearchView, DetailView
from legistar.fields import FieldAggregator, make_item, gen_items
from legistar.base import CachedAttr, DictSetDefault, NoClobberDict


class PersonFields(FieldAggregator):

    @make_item('fullname')
    def get_fullname(self):
        return self.get_field_text('fullname')

    @make_item('website')
    def get_website(self):
        return self.get_field_text('website')

    @make_item('email')
    def get_email(self):
        return self.get_field_text('email')

    @make_item('sources', wrapwith=list)
    def gen_sources(self):
        grouped = collections.defaultdict(set)
        for note, url in self.chainmap['sources'].items():
            grouped[url].add(note)
        for url, notes in grouped.items():
            yield dict(url=url, note=', '.join(notes))


class SearchView(SearchView):
    PUPATYPE = 'people'
    VIEWTYPE = 'search'
    sources_note = 'People search'


class SearchTableRow(TableRow, PersonFields):
    KEY_PREFIX = 'PPL_TABLE'

    def get_detail_url(self):
        return self.get_field_url('fullname')

    def asdict(self):
        '''Combine the detail page data with the table row data.
        '''
        # Get the final data for both.
        data = NoClobberDict(gen_items(self))
        detail_data = dict(self.get_detail_page().asdict())

        # Add any keys detail has that table row doesn't.
        for key in detail_data.keys() - data.keys():
            data[key] = detail_data[key]

        # Add sources and documents.
        listy_fields = ('sources',)
        data = dict(data)
        for key in listy_fields:
            for obj in detail_data[key]:
                if obj not in data[key]:
                    data[key].append(obj)
        return dict(data)


class SearchTable(Table):
    sources_note = 'People search table'


class SearchForm(Form):
    '''Model the legistar people search form.
    '''
    sources_note = 'People search'

    def get_query(self):
        return dict(self.client.state)


class DetailView(DetailView, PersonFields):
    PUPATYPE = 'people'
    KEY_PREFIX = 'PPL_DETAIL'
    sources_note = 'person detail'

    @make_item('district')
    def get_district(self):
        return self.get_field_text('district')

    @make_item('roles', wrapwith=list)
    def gen_roles(self):
        yield from self.viewtype_meta.Form(self)

    @make_item('firstname')
    def get_firstname(self):
        return self.get_field_text('firstname')

    @make_item('lastname')
    def get_lastname(self):
        return self.get_field_text('lastname')



class DetailTable(Table):
    sources_note = 'person detail table'


class DetailTableRow(TableRow):
    KEY_PREFIX = 'PPL_MEMB_TABLE'

    @make_item('org')
    def get_org(self):
        return self.get_field_text('org')

    @make_item('role')
    def get_role(self):
        return self.get_field_text('role')

    @make_item('start_date')
    def get_start_date(self):
        text = self.get_field_text('start_date')
        try:
            return datetime.strptime(text, '%m/%d/%Y')
        except TypeError:
            pass

    @make_item('end_date')
    def get_end_date(self):
        text = self.get_field_text('end_date')
        try:
            return datetime.strptime(text, '%m/%d/%Y')
        except TypeError:
            pass

    @make_item('appointed_by')
    def get_appointed_by(self):
        return self.get_field_text('appointed_by')


class DetailForm(Form):
    skip_first_submit = True
    sources_note = 'person detail'