import re
import json
import time
import collections
from datetime import datetime
from urllib.parse import urlparse, parse_qsl

import lxml.html

from legistar.forms import Form, FirefoxForm
from legistar.tables import Table, TableRow
from legistar.views import SearchView, DetailView
from legistar.fields import FieldAggregator, make_item, gen_items
from legistar.fields import ElementAccessor
from legistar.base import DictSetDefault, NoClobberDict
from legistar.jurisdictions.utils import resolve_name, try_jxn_delegation
# https://github.com/guelo/legistar-scrape/compare/fgregg:master...master


class DateGetter:
    '''Parse a date using the datetime format string defined in
    the current jxn's config.
    '''
    def _get_date(self, label_text):
        fmt = self.get_config_value('datetime_format')
        text = self.get_field_text(label_text)
        if text is not None:
            dt = datetime.strptime(text, fmt)
            dt = self.cfg.datetime_add_tz(dt)
            return dt


class BillsFields(FieldAggregator, DateGetter):

    text_fields = (
        'law_number', 'type', 'status',
        'name', 'version', 'sponsor_office')

    @make_item('intro_date')
    def get_intro_data(self):
        return self._get_date('intro_date')

    @make_item('file_created')
    def get_file_created(self):
        return self._get_date('file_created')

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
        return self.get_field_url('file_number')


class BillsSearchTable(Table):
    sources_note = 'bills search table'


class BillsSearchForm(FirefoxForm):
    '''Model the legistar "Legislation" search form.
    '''
    sources_note = 'bill search table'

    def is_advanced_search(self):
        switch_el_id = self.cfg.BILL_SEARCH_SWITCH_EL_ID
        switch_el = self.firefox.find_element_by_id(switch_el_id)
        switch_el_text = switch_el.text.lower()
        if self.cfg.BILL_SEARCH_SWITCH_SIMPLE in switch_el_text:
            return True
        return False

    def switch_to_advanced_search(self):
        switch_el_id = self.cfg.BILL_SEARCH_SWITCH_EL_ID
        switch_el = self.firefox.find_element_by_id(switch_el_id)
        switch_el.click()

    def fill_out_form(self):
        if not self.is_advanced_search():
            self.switch_to_advanced_search()

        max_results_id = "ctl00_ContentPlaceHolder1_lstMax"
        self.set_dropdown(max_results_id, 'All')

        years_id = "ctl00_ContentPlaceHolder1_lstYearsAdvanced"
        self.set_dropdown(years_id, 'This Year')


class BillsDetailView(DetailView, BillsFields):
    sources_note = 'bill detail'
    text_fields = ('version', 'name')

    @make_item('file_number')
    def get_file_number(self):
        try:
            return self.get_field_text('file_number')
        except:
            msg = (
                'Bill appears to have no file number (bill_id). '
                'Skipping it. If this is wrong, double check the '
                'jurisdiction\'s BILL_DETAIL_TEXT_FILE_NUMBER setting '
                'and make sure it matches the site.')
            self.warning(msg)
            raise self.SkipDocument()

    @make_item('title')
    def get_title(self):
        title = self.get_field_text('title')
        # If no title, re-use type (i.e., "Resolution")
        if not title:
            title = self.get_field_text('type')
        return title

    @make_item('agenda')
    def get_agenda_date(self):
        return self._get_date('agenda')

    @make_item('enactment_date')
    def get_enactment_date(self):
        return self._get_date('enactment_date')

    @make_item('final_action')
    def get_final_action(self):
        return self._get_date('final_action')

    @make_item('sponsors', wrapwith=list)
    def gen_sponsors(self):
        sponsors = self.get_field_text('sponsors')
        for name in re.split(r',\s+', sponsors):
            name = name.strip()
            if name:
                yield dict(name=name)

    @make_item('documents', wrapwith=list)
    def gen_documents(self):
        for el in self.xpath('attachments', './/a'):
            data = ElementAccessor(el)
            url = data.get_url()

            media_type = 'application/pdf'
            # resp = self.client.head(url=url)
            # media_type = resp.headers['content-type']

            yield dict(
                name=data.get_text(),
                links=[dict(
                    url=data.get_url(),
                    media_type=media_type)])

    @make_item('actions', wrapwith=list)
    def gen_action(self):
        yield from self.Form(self)

    @make_item('identifiers', wrapwith=list)
    def gen_identifiers(self):
        '''Yield out the internal legistar bill id and guid found
        in the detail page url.
        '''
        detail_url = self.chainmap['sources'][self.sources_note]
        url = urlparse(detail_url)
        for idtype, ident in parse_qsl(url.query):
            if idtype == 'options' or ident == 'Advanced':
                continue
            yield dict(
                scheme="legistar_" + idtype.lower(),
                identifier=ident)

    @make_item('legislative_session')
    def get_legislative_session(self):
        dates = []
        labels = ('agenda', 'created')
        for label in labels:
            labeltext = self.get_label_text(label, skipitem=False)
            if labeltext not in self.field_data.keys():
                continue
            if not self.field_data[labeltext]:
                continue
            data = self.field_data[labeltext][0]
            fmt = self.get_config_value('datetime_format')
            text = data.get_text()
            if text is not None:
                dt = datetime.strptime(text, fmt)
                dt = self.cfg.datetime_add_tz(dt)
                dates.append(dt)

        _, actions = self.gen_action()
        for action in actions:
            dates.append(action['date'])

        if dates:
            return str(max(dates).year)

        self.critical('Need session date.')
        import pdb; pdb.set_trace()

class BillsDetailTable(Table):
    sources_note = 'bill detail table'


class BillsDetailForm(Form):
    skip_first_submit = True
    sources_note = 'bill detail'


class BillsDetailTableRow(TableRow, FieldAggregator, DateGetter):
    sources_node = 'bill action table'
    disable_aggregator_funcs = True
    text_fields = (
        ('action_by', 'organization'),
        ('action', 'text'),
        'version',
        'result',
        'journal_page',
        )

    def get_detail_viewtype(self):
        return BillsDetailAction

    def get_detail_url(self):
        return self.get_media_url('action_details')

    @make_item('date')
    def get_date(self):
        return self._get_date('date')

    def _get_media(self, label):
        '''Given a field label, get it's url (if any) and send a head
        request to determine the content_type. Return a dict.
        '''
        data = self.get_field_data(label)
        url = data.get_url()
        if url is None:
            raise self.SkipItem()
        self.info('Sending HEAD request for %r' % url)
        media_type = 'application/pdf'
        # resp = self.client.head(url=url)
        # media_type = resp.headers['content-type']
        return dict(
            name=data.get_text(),
            links=[dict(
                url=data.get_url(),
                media_type=media_type)])

    @make_item('media', wrapwith=list)
    def gen_media(self):
        for label in self.get_config_value('pupa_media'):
            try:
                yield self._get_media(label)
            except self.SkipItem:
                continue


class ActionBase(FieldAggregator):
    disable_aggregator_funcs = True

    def get_prefix(self):
        '''The settings prefix for this view.
        '''
        return 'BILL_ACTION'


class BillsDetailAction(DetailView, ActionBase):
    sources_note = 'bill action detail'

    text_fields = (
        'file_number', 'type', 'title', 'mover', 'seconder',
        'result', 'agenda_note', 'minutes_note', 'action',
        'action_text')

    @make_item('votes', wrapwith=list)
    def gen_votes(self):
        table_path = self.get_config_value('table_class')
        Table = resolve_name(table_path)
        yield from self.make_child(Table, self)

    @make_item('sources', wrapwith=list)
    def gen_sources(self):
        yield dict(url=self.url, note='action detail')


class BillsDetailActionTable(Table, ActionBase):
    sources_note = 'bill action detail table'

    def get_table_cell_type(self):
        path = self.get_config_value('tablecell_class')
        return resolve_name(path)

    def get_table_row_type(self):
        path = self.get_config_value('tablerow_class')
        return resolve_name(path)


class BillsDetailActionTableRow(TableRow, ActionBase):
    sources_node = 'bill action detail table'
    text_fields = ('person', 'vote')
