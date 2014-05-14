import re
from datetime import datetime

from hercules import CachedAttr, DictSetDefault

from legistar.base.table import Table, TableRow
from legistar.utils.itemgenerator import make_item, gen_items
from legistar.events.field import EventFields


class TableRow(TableRow, EventFields):
    KEY_PREFIX = 'EVT_TABLE'

    def get_detail_url(self):
        return self.get_field_url('details')

    @CachedAttr
    def ical_data(self):
        ical_url = self.get_ical_url()
        self.debug('%r is fetching ical data: %r', self, ical_url)
        resp = self.cfg.client.session.get(ical_url)
        with DictSetDefault(self.ctx, 'sources', {}) as sources:
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
        detail_data = dict(self.detail_page.asdict())

        # Add any keys detail has that table row doesn't.
        for key in detail_data.keys() - data.keys():
            data[key] = detail_data[key]

        # Add sources and documents.
        listy_fields = ('sources', 'documents', 'participants')
        for key in listy_fields:
            for obj in detail_data[key]:
                if obj not in data[key]:
                    data[key].append(obj)
        return data


class Table(Table):
    sources_note = 'Events search table'
