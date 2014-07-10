import datetime

import pupa.scrape

from legistar.utils.itemgenerator import make_item
from legistar.ext.pupa.base import Adapter, Converter


class AgendaItemAdapter(Adapter):
    aliases = []
    extras_keys = [
        'action', 'action_details', 'file_number',
        'version', 'type', 'result']

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
        for data in self.data.get('agenda'):
            yield AgendaItemAdapter(data).get_instance_data()

    @make_item('all_day')
    def get_all_day(self):
        length = self.data['end_time'] - self.data['start_time']
        if datetime.timedelta(hours=6) - length:
            return True
        else:
            return False

    def add_agenda_data(self, agenda_item, data):
        media = data.pop('media', [])
        entities = data.pop('entities', [])
        subjects = data.pop('subjects', [])

        for media in media:
            agenda_item.add_media_link(**media)
        for entity in entities:
            agenda_item.add_entity(**media)
        for subjects in subjects:
            agenda_item.add_subject(**subject)


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
            instance.add_document(**document)
        for source in sources:
            instance.add_source(**source)

        instance.extras.update(extras)

        for agenda_data in agenda:
            description = agenda_data.pop('description')
            agenda_item = instance.add_agenda_item(description)
            self.add_agenda_data(agenda_item, agenda_data)

        return instance

class EventsConverter(Converter):
    adapter = EventsAdapter
