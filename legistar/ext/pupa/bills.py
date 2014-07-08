import datetime

import pupa.scrape

from legistar.utils.itemgenerator import make_item
from legistar.ext.pupa.base import Adapter, Converter


def _get_date(date):
    if isinstance(date, datetime.datetime):
        return date.strftime('%Y-%m-%d')
    else:
        return date

class ActionAdapter(Adapter):
    aliases = [
        ('text', 'description'),
        ]
    extras_keys = ['version', 'media', 'result']

    @make_item('date')
    def get_date(self):
        return _get_date(self.data['date'])


class VoteAdapter(Adapter):
    text_fields = ['organization']
    aliases = [
        ('text', 'motion_text'),
        ]
    drop_keys = ['votes']
    extras_keys = ['version']

    @make_item('start_date')
    def get_date(self):
        return _get_date(self.data['date'])

    @make_item('votes', wrapwith=list)
    def gen_votes(self):
        for data in self.data['votes']:
            res = {}
            res['option'] = self.get_vote_option(data['vote'])
            res['voter'] = data['person']
            yield data

# (self, *, legislative_session, motion_text, start_date, classification, result,
#                  identifier='', bill=None, organization=None, chamber=None, **kwargs):

    # ------------------------------------------------------------------------
    # Overridables
    # ------------------------------------------------------------------------
    @try_jxn_delegation
    def get_vote_result(self, data):
        '''
        '''
        raise NotImplemented()

    @try_jxn_delegation
    def get_vote_option(self, option_text):
        return self.cfg._BILL_VOTE_OPTION_MAP[option_text]


class BillsAdapter(Adapter):
    pupa_model = pupa.scrape.Bill
    aliases = [
        ('file_number', 'identifier'),
        ]
    extras_keys = ['law_number', 'status']

    @make_item('classification')
    def get_classn(self):
        return self.get_bill_classification(self.data.pop('type'))

    @make_item('actions', wrapwith=list)
    def gen_actions(self):
        for data in self.data.get('actions'):
            data = dict(data)
            data.pop('votes')
            yield self.make_child(ActionAdapter, data).get_instance_data()

    @make_item('sponsorships')
    def get_sponsorships(self):
        return self.data['sponsors']

    @make_item('votes', wrapwith=list)
    def gen_votes(self):
        for data in self.data.get('actions'):
            for vote in data.get('votes', []):
                more_data = dict(legislative_session=)
                yield self.make_child(VoteAdapter, data).get_instance_data()

    @make_item('subject')
    def _gen_subjects(self, wrapwith=list):
        yield from self.gen_subjects()

    def get_instance(self):
        '''Build a pupa instance from the data.
        '''
        data = self.get_instance_data()
        data_copy = dict(data)
        bill = pupa.scrape.Bill(
            identifier=data['identifier'],
            legislative_session=data['legislative_session'],
            classification=data.get('classification', []),
            title=data['title'],
            )

        for action in data.pop('actions'):
            action.pop('extras')
            bill.add_action(**action)

        for sponsor in data.pop('sponsors'):
            if not self.drop_sponsor(sponsor):
                kwargs = dict(
                    classification=self.get_sponsor_classification(sponsor),
                    entity_type=self.get_sponsor_entity_type(sponsor),
                    primary=self.get_sponsor_primary(sponsor))
                kwargs.update(sponsor)
                bill.add_sponsorship(**kwargs)

        import pdb; pdb.set_trace()

        return bill

    # ------------------------------------------------------------------------
    # Overridables: sponsorships
    # ------------------------------------------------------------------------
    @try_jxn_delegation
    def drop_sponsor(self, data):
        '''If this function retruns True, the sponsor is dropped.
        '''
        return False

    @try_jxn_delegation
    def get_sponsor_classification(self, data):
        '''Return the sponsor's pupa classification. Legistar generally
        doesn't provide any info like this, so we just return "".
        '''
        return ''

    @try_jxn_delegation
    def get_sponsor_entity_type(self, data):
        '''Return the sponsor's pupa entity type.
        '''
        return 'person'

    @try_jxn_delegation
    def get_sponsor_primary(self, data):
        '''Return whether the sponsor is primary. Legistar generally doesn't
        provide this.
        '''
        return False

    # ------------------------------------------------------------------------
    # Overridables: miscellaneous
    # ------------------------------------------------------------------------
    @try_jxn_delegation
    def gen_subjects(self, data):
        '''Get whatever data from the scraped data represents subjects.
        '''
        raise StopIteration()

    @try_jxn_delegation
    def get_bill_classification(self, billtype):
        '''Convert the legistar bill `type` column into
        a pupa classification array.
        '''
        # Try to get the classn from the subtype.
        classn = getattr(self, '_BILL_CLASSIFICATIONS', {})
        classn = dict(classn).get(billtype)
        if classn is not None:
            return [classn]

        # Bah, no matches--try to guess it.
        type_lower = billtype.lower()
        for classn in dict(ocd_common.BILL_CLASSIFICATION_CHOICES):
            if classn in type_lower:
                return [classn]

        # None found; return emtpy array.
        return []


class BillsConverter(Converter):
    adapter = BillsAdapter
