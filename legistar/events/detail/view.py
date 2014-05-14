from datetime import datetime

from legistar.base.detailview import DetailView
from legistar.base.field import make_item
from legistar.events.field import EventFields


class DetailView(DetailView, EventFields):
    PUPATYPE = 'events'
    sources_note = 'Event detail'

    @make_item('agenda', wrapwith=list)
    def gen_agenda(self):
        yield from self.viewtype_meta.Form(self)
