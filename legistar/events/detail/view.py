from datetime import datetime

from legistar.base.detailview import DetailView
from legistar.base.field import make_item
from legistar.events.field import EventFields


class DetailView(DetailView, EventFields):
    PUPATYPE = 'events'
    sources_note = 'Event detail'

    @make_item('when')
    def get_when(self):
        date = self.field_data[self.cfg.EVT_DETAIL_TEXT_DATE].text
        time = self.field_data[self.cfg.EVT_DETAIL_TEXT_TIME].text
        dt = datetime.strptime(
            '%s %s' % (date, time), self.cfg.EVT_DETAIL_DATETIME_FORMAT)
        return dt

    @make_item('location')
    def get_location(self):
        return self.field_data[self.cfg.EVT_DETAIL_TEXT_LOCATION].text

    @make_item('agenda', wrapwith=list)
    def gen_agenda(self):
        yield from self.viewtype_meta.Form(self)
