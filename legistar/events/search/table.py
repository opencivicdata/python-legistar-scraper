import re
from datetime import datetime

from hercules import CachedAttr, DictSetDefault

from legistar.base.table import Table, TableRow
from legistar.utils.itemgenerator import make_item, gen_items
from legistar.events.field import EventFields


class TableRow(TableRow, EventFields):
    KEY_PREFIX = 'EVT_TABLE'

    def get_detail_url(self):
        key = self.get_label_text('details')
        return self.field_data[key].get_url()

    @CachedAttr
    def ical_data(self):
        ical_url = self.get_ical_url()
        resp = self.cfg.client.session.get(ical_url)
        with DictSetDefault(self.ctx, 'sources', {}) as sources:
            sources['Event icalendar data (end date)'] = ical_url
        return resp.text

    def get_ical_url(self):
        key = self.get_label_text('ical')
        return self.field_data[key].get_url()

    @make_item('name')
    def get_name(self):
        key = self.get_label_text('topic')
        return self.field_data[key].get_text()

    @make_item('end')
    def get_end(self):
        end_time = re.search(r'DTEND:([\dT]+)', self.ical_data).group(1)
        dt = datetime.strptime(end_time, r'%Y%m%dT%H%M%S')
        return dt

    def asdict(self):
        return dict(gen_items(self))


class Table(Table):
    sources_note = 'Events search table'
