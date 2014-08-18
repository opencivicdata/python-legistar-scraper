import re
import json
import collections
from datetime import datetime

from legistar.forms import Form, FirefoxForm
from legistar.tables import Table, TableRow
from legistar.views import SearchView, DetailView
from legistar.base import DictSetDefault, Adapter, Converter

import pupa.scrape




class EventsFields(FieldAggregator):

    def get_location(self):
        location = self.get_field_text('location') or 'City Hall'
        location = location.strip(' \n"')
        return location

    def get_name(self):
        return self.get_field_text('name') or 'Meeting'

    def get_description(self):
        return self.get_field_text('topic') or 'Meeting'

    def gen_media(self):
        for key in self.get_config_value('PUPA_MEDIA'):
            try:
                field = self.get_field_data(key)
            except self.SkipItem:
                continue

            # This column isn't present on this legistar instance.
            if field is None:
                continue
            elif field.is_blank():
                continue
            elif field.get_media_url() is None:
                continue

            media = dict(
                note=field.get_text(),
                url=field.get_media_url(),
                media_type=field.get_media_type() or '')
            yield media

    def gen_documents(self):
        for key in self.get_config_value('PUPA_DOCUMENTS'):
            try:
                field = self.get_field_data(key)
            except self.SkipItem:
                continue

            # This column isn't present on this legistar instance.
            if field is None:
                continue
            elif field.is_blank():
                continue
            elif field.get_url() is None:
                continue
            document = dict(
                note=field.get_text(),
                url=field.get_url(),
                media_type=field.get_media_type())
            yield document

    def gen_participants(self):
        participant_fields = self.get_config_value('PUPA_PARTICIPANTS')
        for entity_type, keys in participant_fields.items():
            for key in keys:
                try:
                    cell = self.get_field_data(key)
                except self.SkipItem:
                    continue

                # But it's often the name of a committee we can add as a
                # participant.
                participant = dict(name=cell.text, type=entity_type)
                yield participant

    def gen_sources(self):
        grouped = collections.defaultdict(set)
        for note, url in self.chainmap['sources'].items():
            grouped[url].add(note)
        for url, notes in grouped.items():
            yield dict(url=url, note=', '.join(sorted(notes)))


class EventsSearchView(SearchView):
    sources_note = 'events search'


class EventsSearchTableRow(TableRow, EventsFields):

    def get_detail_url(self):
        return self.get_field_url('details')

    def get_ical_data(self):
        if hasattr(self, '_cal_data'):
            return self._ical_data
        # Don't fetch the ical data if we're testing.
        ical_url = self.get_ical_url()
        self.debug('%r is fetching ical data: %r', self, ical_url)
        resp = self.cfg.client.session.get(ical_url)
        with DictSetDefault(self.chainmap, 'sources', {}) as sources:
            sources['Event icalendar data (end date)'] = ical_url
        self._ical_data = resp.text
        return self._ical_data

    def get_ical_url(self):
        return self.get_field_url('ical')

    def get_name(self):
        '''The pupa name of the meeting. In some jurisdictions,
        the topic field will be better. But it caused dupes
        in NYC.
        '''
        name = self.get_field_text('name')
        return name

    def get_end(self):
        '''Get the event end date from the ical record.
        '''
        end_time = re.search(r'DTEND:([\dT]+)', self.get_ical_data()).group(1)
        dt = datetime.strptime(end_time, r'%Y%m%dT%H%M%S')
        dt = self.cfg.datetime_add_tz(dt)
        return dt

    def get_when(self):
        '''Get the event start date from the ical record.
        '''
        end_time = re.search(r'DTSTART:([\dT]+)', self.get_ical_data()).group(1)
        dt = datetime.strptime(end_time, r'%Y%m%dT%H%M%S')
        dt = self.cfg.datetime_add_tz(dt)
        return dt


class EventsSearchTable(Table):
    sources_note = 'events search table'


class EventsSearchForm(FirefoxForm):
    '''Model the legistar "Calendar" search form.
    '''
    sources_note = 'events search table'

    def fill_out_form(self):
        self.set_dropdown('ctl00_ContentPlaceHolder1_lstYears', 'This Year')


class EventsDetailView(DetailView, EventsFields):
    sources_note = 'event detail'


    def gen_agenda(self):
        yield from self.Form(self)


class EventsDetailTable(Table):
    sources_note = 'event detail table'


class EventsDetailTableRow(TableRow):

    # Maps the 'type' field in event detail tables to pupa type.
    typetext_map = {
        'ordinance': 'bill',
        'bill': 'bill',
        'resolution': 'resolution'}

    def _get_type(self):
        typetext = self.get_field_text('type')
        if typetext is not None:
            typetext = typetext.lower()
        return self.typetext_map.get(typetext, 'note')

    def get_version(self):
        return self.get_field_text('version')

    def get_description(self):
        return self.get_field_text('title') or 'Meeting'

    def get_agenda_num(self):
        return self.get_field_text('agenda_number')

    def get_subjects(self):
        subject = self.get_field_text('name')
        if subject is not None:
            yield subject

    def get_type(self):
        return self._get_type()

    def get_name(self):
        return self.get_field_text('name')

    def get_action(self):
        return self.get_field_text('action')

    def get_result(self):
        return self.get_field_text('result')

    def get_details(self):
        return self.get_field_text('action_details')

    def get_transcript_url(self):
        return self.get_field_url('transcript')

    def get_file_number(self):
        '''Get the bill id from a table row of related bills on an Event
        detail page.
        '''
        return self.get_field_text('file_number')

    def get_detail_url(self):
        '''Get detail url of an agenda item.
        '''
        return self.get_field_url('file_number')

    def gen_media(self):
        for key in self.get_config_value('PUPA_MEDIA'):
            try:
                field = self.get_field_data(key)
            except self.SkipItem:
                continue

            # This column isn't present on this legistar instance.
            if field is None:
                continue
            elif field.is_blank():
                continue
            elif field.get_media_url() is None:
                continue

            media = dict(
                note=field.get_text(),
                url=field.get_media_url(),
                media_type=field.get_media_type())
            yield media


class EventsDetailForm(Form):
    skip_first_submit = True
    sources_note = 'event detail'

    def get_query(self, **kwargs):
        return kwargs


class AgendaItemAdapter(Adapter):
    aliases = []
    extras_keys = [
        'action', 'action_details', 'file_number',
        'version', 'type', 'result']
    drop_keys = ['date']

    #make_item('related_entities', wrapwith=list)
    def gen_related_entities(self):
        url = self.data.get('url')
        if url is None:
            return
        if 'LegislationDetail' in url:
            data = {
                'type': 'bill',
                'id': self.data['file_number'],
                'name': self.data['name'],
                'note': self.data['description'],
                }
            yield data

    def get_instance(self, **extra_instance_data):
        return self.get_instance_data(**extra_instance_data)


class EventsAdapter(Adapter):
    pupa_model = pupa.scrape.Event
    aliases = []
    extras_keys = []

    #make_item('agenda', wrapwith=list)
    def gen_agenda(self):
        for data in self.data.get('agenda', []):
            yield AgendaItemAdapter(data).get_instance_data()

    #make_item('all_day')
    def get_all_day(self):
        length = self.data['end_time'] - self.data['start_time']
        zero = datetime.timedelta()
        # If it's 6 hours or less, it's just a partial day meeting.
        if zero <= (datetime.timedelta(hours=6) - length):
            return False
        else:
            return True

    #make_item('timezone')
    def get_timezone(self):
        return self.cfg.TIMEZONE

    def add_agenda_data(self, agenda_item, data):
        media = data.pop('media', [])
        entities = data.pop('entities', [])
        subjects = data.pop('subjects', [])

        for media in media:
            agenda_item.add_media_link(**media)
        for entity in entities:
            agenda_item.add_entity(**entity)
        for subject in subjects:
            agenda_item.add_subject(subject)

    def get_instance(self, **extra_instance_data):
        instance_data = self.get_instance_data(**extra_instance_data)

        media = instance_data.pop('media', [])
        participants = instance_data.pop('participants', [])
        documents = instance_data.pop('documents', [])
        agenda = instance_data.pop('agenda', [])
        extras = instance_data.pop('extras', [])
        sources = instance_data.pop('sources', [])

        instance = self.pupa_model(**instance_data)

        for media in media:
            instance.add_media_link(**media)
        for participant in participants:
            instance.add_participant(**participant)
        for document in documents:
            instance.add_document(on_duplicate='ignore', **document)
        for source in sources:
            instance.add_source(**source)

        instance.extras.update(extras)

        for agenda_data in agenda:
            description = agenda_data.pop('description', '')
            if not description:
                continue
            agenda_item = instance.add_agenda_item(description)
            self.add_agenda_data(agenda_item, agenda_data)

        key = self.get_cache_key(instance)
        if key in self.cfg.event_cache:
            event1 = self.cfg.event_cache[key]
            event2 = instance
            return self.merge_events(event1, event2)
        else:
            self.cfg.event_cache[key] = instance
            return instance

    def get_cache_key(self, instance):
        '''Events with the same time, place, and name
        are considered a single event.
        '''
        return (
            instance.name,
            instance.start_time,
            instance.end_time,
            frozenset(instance.location.items())
            )

    def merge_events(self, event1, event2):
        event1.media.extend(event2.media)
        event1.documents.extend(event2.documents)
        event1.sources.extend(event2.sources)
        event1.participants.extend(event2.participants)
        event1.agenda.extend(event2.agenda)
        return event1


class EventsConverter(Converter):
    adapter = EventsAdapter
