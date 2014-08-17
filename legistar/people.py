import re
import json
import collections
from datetime import datetime
from urllib.parse import urlparse, parse_qsl

from legistar.forms import Form
from legistar.tables import Table, TableRow
from legistar.views import SearchView, DetailView
from legistar.fields import FieldAggregator, make_item, gen_items


class PeopleFields(FieldAggregator):

    @make_item('fullname')
    def get_fullname(self):
        return self.get_field_text('fullname')

    @make_item('district')
    def get_district(self):
        return self.get_field_text('district')

    @make_item('website')
    def get_website(self):
        return self.get_field_url('website')

    @make_item('email')
    def get_email(self):
        return self.get_field_text('email')

    @make_item('sources', wrapwith=list)
    def gen_sources(self):
        grouped = collections.defaultdict(set)
        for note, url in self.chainmap['sources'].items():
            grouped[url].add(note)
        for url, notes in grouped.items():
            yield dict(url=url, note=', '.join(sorted(notes)))

    @make_item('fax')
    def get_fax(self):
        self.warning('Fax is not supported in current pupa spec; skipped it.')
        raise self.SkipItem()
        return self.get_field_text('fax')

    @make_item('district_phone')
    def get_district_phone(self):
        return self.get_field_text('district_phone')

    @make_item('district_address')
    def get_district_address(self):
        return self.get_field_text('district_address')

    @make_item('district_address_state')
    def get_state(self):
        return self.get_field_text('district_address_state')

    @make_item('district_address_city')
    def get_district_address_city(self):
        return self.get_field_text('district_address_city')

    @make_item('district_address_zip')
    def get_district_address_zip(self):
        return self.get_field_text('district_address_zip')

    @make_item('cityhall_address_state')
    def get_cityhall_state(self):
        return self.get_field_text('cityhall_address_state')

    @make_item('cityhall_phone')
    def get_cityhall_phone(self):
        return self.get_field_text('cityhall_phone')

    @make_item('cityhall_address')
    def get_cityhall_address(self):
        return self.get_field_text('cityhall_address')

    @make_item('cityhall_address_city')
    def get_cityhall_address_city(self):
        return self.get_field_text('cityhall_address_city')

    @make_item('cityhall_address_zip')
    def get_cityhall_address_zip(self):
        return self.get_field_text('cityhall_address_zip')


class PeopleSearchView(SearchView):
    sources_note = 'People search'


class PeopleSearchTableRow(TableRow, PeopleFields):
    def get_detail_url(self):
        return self.get_field_url('fullname')


class PeopleSearchTable(Table):
    sources_note = 'people search table'


class PeopleSearchForm(Form):
    '''Model the legistar people search form.
    '''
    sources_note = 'people search'
    def get_query(self):
        return dict(self.client.state)


class PeopleDetailView(DetailView, PeopleFields):
    sources_note = 'person detail'

    @make_item('notes')
    def get_district(self):
        return self.get_field_text('notes')

    @make_item('memberships', wrapwith=list)
    def gen_roles(self):
        yield from self.Form(self)

    @make_item('firstname')
    def get_firstname(self):
        return self.get_field_text('firstname')

    @make_item('lastname')
    def get_lastname(self):
        return self.get_field_text('lastname')

    @make_item('image')
    def get_photo_url(self):
        return self.get_field_img_src('Photo')

    @make_item('identifiers', wrapwith=list)
    def gen_identifiers(self):
        '''Yield out the internal legistar person id and guid found
        in the detail page url.
        '''
        detail_url = self.chainmap['sources'][self.sources_note]
        url = urlparse(detail_url)
        for idtype, ident in parse_qsl(url.query):
            yield dict(
                scheme="legistar_" + idtype.lower(),
                identifier=ident)


class PeopleDetailTable(Table):
    sources_note = 'person detail table'


class PeopleDetailForm(Form):
    skip_first_submit = True
    sources_note = 'person detail'


class PeopleDetailTableRow(TableRow):

    @make_item('org')
    def get_org(self):
        return self.get_field_text('org')

    @make_item('role')
    def get_role(self):
        return self.get_field_text('role')

    @make_item('start_date')
    def get_start_date(self):
        text = self.get_field_text('start_date')
        if text is None:
            return
        text = text.strip("*")
        try:
            dt = datetime.strptime(text, '%m/%d/%Y')
            dt = self.cfg.datetime_add_tz(dt)
            return dt
        except TypeError:
            pass

    @make_item('end_date')
    def get_end_date(self):
        text = self.get_field_text('end_date')
        if text is None:
            return
        text = text.strip("*")
        try:
            dt = datetime.strptime(text, '%m/%d/%Y')
            dt = self.cfg.datetime_add_tz(dt)
            return dt
        except TypeError:
            pass

    @make_item('appointed_by')
    def get_appointed_by(self):
        return self.get_field_text('appointed_by')
