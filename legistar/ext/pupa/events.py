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


class EventsConverter(Converter):
    adapter = EventsAdapter
