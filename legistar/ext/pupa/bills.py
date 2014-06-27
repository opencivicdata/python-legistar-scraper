import pupa.scrape

from legistar.utils.itemgenerator import make_item
from legistar.ext.pupa.base import Adapter, Converter


class ActionAdapter(Adapter):
    aliases = [
        ('text', 'description'),
        ]
    extras_keys = ['version', 'media']

    @make_item('type')
    def get_type(self):
        return []


class BillsAdapter(Adapter):
    pupa_model = pupa.scrape.Bill
    aliases = []
    extras_keys = []

    @make_item('session')
    def get_session(self):
        import pdb; pdb.set_trace()

    @make_item('actions', wrapwith=list)
    def gen_actions(self):
        for data in self.data.get('actions'):
            yield ActionAdapter(data).get_instance_data()


class BillsConverter(Converter):
    adapter = BillsAdapter
