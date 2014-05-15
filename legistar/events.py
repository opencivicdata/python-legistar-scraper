import re
import json
import collections
from datetime import datetime

from legistar.forms import Form
from legistar.tables import Table, TableRow
from legistar.views import SearchView, DetailView
from legistar.fields import FieldAggregator, make_item, gen_items
from legistar.base import CachedAttr, DictSetDefault, NoClobberDict


class EventFields(FieldAggregator):

    @make_item('location')
    def get_location(self):
        return self.get_field_text('location')

    @make_item('documents', wrapwith=list)
    def gen_documents(self):
        for key in self.get_config_value('PUPA_DOCUMENTS'):
            field = self.field_data.get(key)

            # This column isn't present on this legistar instance.
            if field is None:
                continue
            elif field.is_blank():
                continue
            elif field.get_url() is None:
                continue
            document = dict(
                name=field.get_text(),
                url=field.get_url(),
                mimetype=field.get_mimetype())
            yield document

    @make_item('participants', wrapwith=list)
    def gen_participants(self):
        participant_fields = self.get_config_value('PUPA_PARTICIPANTS')
        for entity_type, keys in participant_fields.items():
            for key in keys:
                cell = self.field_data[key]
                participant = dict(name=cell.text, type=entity_type)
                yield participant

    @make_item('sources', wrapwith=list)
    def gen_sources(self):
        grouped = collections.defaultdict(set)
        for note, url in self.chainmap['sources'].items():
            grouped[url].add(note)
        for url, notes in grouped.items():
            yield dict(url=url, note=', '.join(notes))


class SearchView(SearchView):
    PUPATYPE = 'events'
    VIEWTYPE = 'search'
    sources_note = 'Events search'


class SearchTableRow(TableRow, EventFields):
    KEY_PREFIX = 'EVT_TABLE'

    def get_detail_url(self):
        return self.get_field_url('details')

    @CachedAttr
    def ical_data(self):
        ical_url = self.get_ical_url()
        self.debug('%r is fetching ical data: %r', self, ical_url)
        resp = self.cfg.client.session.get(ical_url)
        with DictSetDefault(self.chainmap, 'sources', {}) as sources:
            sources['Event icalendar data (end date)'] = ical_url
        return resp.text

    def get_ical_url(self):
        return self.get_field_url('ical')

    @make_item('name')
    def get_name(self):
        '''The pupa name, or Legistar "topic" of the meeting.
        '''
        return self.get_field_text('topic')

    @make_item('end')
    def get_end(self):
        '''Get the event end date from the ical record.
        '''
        end_time = re.search(r'DTEND:([\dT]+)', self.ical_data).group(1)
        dt = datetime.strptime(end_time, r'%Y%m%dT%H%M%S')
        return dt

    @make_item('when')
    def get_when(self):
        '''Get the event start date from the ical record.
        '''
        end_time = re.search(r'DTSTART:([\dT]+)', self.ical_data).group(1)
        dt = datetime.strptime(end_time, r'%Y%m%dT%H%M%S')
        return dt

    def asdict(self):
        '''Combine the detail page data with the table row data.
        '''
        # Get the final data for both.
        data = dict(gen_items(self))
        if not self.cfg.EVT_DETAIL_AVAILABLE:
            return data

        data = NoClobberDict(data)
        detail_data = dict(self.get_detail_page().asdict())

        # Add any keys detail has that table row doesn't.
        for key in detail_data.keys() - data.keys():
            data[key] = detail_data[key]

        # Add sources and documents.
        listy_fields = ('sources', 'documents', 'participants')
        data = dict(data)
        for key in listy_fields:
            for obj in detail_data[key]:
                if obj not in data[key]:
                    data[key].append(obj)
        return dict(data)


class SearchTable(Table):
    sources_note = 'Events search table'


class SearchForm(Form):
    '''Model the legistar "Calendar" search form.
    '''
    sources_note = 'Events search'

    def get_query(self, time_period=None, bodies=None):
        time_period = time_period or self.cfg.EVENTS_SEARCH_TIME_PERIOD
        bodies = bodies or self.cfg.EVENTS_SEARCH_BODIES
        clientstate = json.dumps({'value': time_period})

        query = {
            self.cfg.EVENTS_SEARCH_BODIES_EL_NAME: bodies,
            self.cfg.EVENTS_SEARCH_TIME_PERIOD_EL_NAME: time_period,
            self.cfg.EVENTS_SEARCH_CLIENTSTATE_EL_NAME: clientstate,
            }
        self.debug('Query is %r' % query)
        query = dict(self.client.state, **query)
        return query


class DetailView(DetailView, EventFields):
    PUPATYPE = 'events'
    KEY_PREFIX = 'EVT_DETAIL'
    sources_note = 'Event detail'

    @make_item('agenda', wrapwith=list)
    def gen_agenda(self):
        yield from self.viewtype_meta.Form(self)


class DetailTable(Table):
    sources_note = 'Event detail table'


class DetailTableRow(TableRow):
    KEY_PREFIX = 'EVT_AGENDA_TABLE'

    # Maps the 'type' field in event detail tables to pupa type.
    typetext_map = {
        'ordinance': 'bill',
        'bill': 'bill',
        'resolution': 'resolution'}

    def _get_type(self):
        typetext = self.get_field_text('type')
        if typetext is not None:
            typetext = typetext.lower()
        return self.typetext_map.get(typetext, 'document')

    @make_item('version')
    def get_version(self):
        return self.get_field_text('version')

    @make_item('agenda_num')
    def get_agenda_num(self):
        return self.get_field_text('agenda_number')

    @make_item('subject')
    def get_subject(self):
        return self.get_field_text('name')

    @make_item('type')
    def get_type(self):
        return self._get_type()

    @make_item('name')
    def get_name(self):
        return self.get_field_text('title')

    @make_item('action')
    def get_action(self):
        return self.get_field_text('action')

    @make_item('result')
    def get_result(self):
        return self.get_field_text('result')

    @make_item('action_details')
    def get_details(self):
        return self.get_field_text('action_details')

    @make_item('video_url')
    def get_video_url(self):
        return self.get_field_url('video')

    @make_item('audio_url')
    def get_audio_url(self):
        return self.get_field_url('audio')

    @make_item('transcript_url')
    def get_transcript_url(self):
        return self.get_field_url('transcript')

    @make_item('file_number')
    def get_file_number(self):
        '''Get the bill id from a table row of related bills on an Event
        detail page.
        '''
        return self.get_field_text('file_number')


class DetailForm(Form):
    skip_first_submit = True
    sources_note = 'Event detail'