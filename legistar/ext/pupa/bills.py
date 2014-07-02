import pupa.scrape

from legistar.utils.itemgenerator import make_item
from legistar.ext.pupa.base import Adapter, Converter


class ActionAdapter(Adapter):
    aliases = [
        ('text', 'description'),
        ]
    extras_keys = ['version', 'media']

    @make_item('date')
    def get_date(self):
        return self.data.pop('date').strftime('%Y-%m-%d')


class BillsAdapter(Adapter):
    pupa_model = pupa.scrape.Bill
    aliases = [
        ('file_number', 'identifier'),
        ]
    extras_keys = ['law_number', 'status']

    @make_item('classification')
    def get_classn(self):
        return self.cfg.get_bill_classification(self.data.pop('type'))

    @make_item('actions', wrapwith=list)
    def gen_actions(self):
        for data in self.data.get('actions'):
            yield ActionAdapter(data).get_instance_data()

    @make_item('sponsorships')
    def get_sponsorships(self):
        return self.data.pop('sponsors', [])


class BillsConverter(Converter):
    adapter = BillsAdapter
