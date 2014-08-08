import datetime

import pupa.scrape

from legistar.utils.itemgenerator import make_item
from legistar.ext.pupa.base import Adapter, Converter


class AgendaItemAdapter(Adapter):
    aliases = []
    extras_keys = [
        'action', 'action_details', 'file_number',
        'version', 'type', 'result']
    drop_keys = ['date']

    @make_item('related_entities', wrapwith=list)
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

    @make_item('agenda', wrapwith=list)
    def gen_agenda(self):
        for data in self.data.get('agenda', []):
            yield AgendaItemAdapter(data).get_instance_data()

    @make_item('all_day')
    def get_all_day(self):
        length = self.data['end_time'] - self.data['start_time']
        zero = datetime.timedelta()
        # If it's 6 hours or less, it's just a partial day meeting.
        if zero <= (datetime.timedelta(hours=6) - length):
            return False
        else:
            return True

    @make_item('timezone')
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
