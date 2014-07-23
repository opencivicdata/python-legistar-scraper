import datetime
import collections

import pupa.scrape
from opencivicdata import common as ocd_common

from legistar.utils.itemgenerator import make_item
from legistar.jurisdictions.utils import try_jxn_delegation
from legistar.ext.pupa.base import Adapter, Converter


def _get_date(date):
    if isinstance(date, datetime.datetime):
        return date.strftime('%Y-%m-%d')
    else:
        return date

class ActionAdapter(Adapter):
    aliases = [('text', 'description')]
    extras_keys = ['version', 'media', 'result']
    drop_keys = ['sources']

    @make_item('date')
    def get_date(self):
        return _get_date(self.data['date'])


class VoteAdapter(Adapter):
    pupa_model = pupa.scrape.Vote
    text_fields = ['organization']
    aliases = [
        ('text', 'motion_text'),
        ]
    drop_keys = ['date']
    extras_keys = ['version', 'media']

    @make_item('start_date')
    def get_date(self):
        return _get_date(self.data.get('date'))

    @make_item('result')
    def get_result(self):
        if not self.data['result']:
            raise self.SkipItem()
        return self.get_vote_result(self.data['result'])

    @make_item('votes', wrapwith=list)
    def gen_votes(self):
        for data in self.data['votes']:
            res = {}
            res['option'] = self.get_vote_option(data['vote'])
            res['note'] = data['vote']
            res['voter'] = data['person']
            yield res

    def get_instance(self, **extra_instance_data):
        data = self.get_instance_data()
        data.update(extra_instance_data)

        motion_text = data['motion_text']
        data['classification'] = self.classify_motion_text(motion_text)

        # Drop the org if necessary. When org is the top-level org, omit.
        if self.drop_organization(data):
            data.pop('organization', None)

        vote_data_list = data.pop('votes')
        extras = data.pop('extras')
        sources = data.pop('sources')

        vote = self.pupa_model(**data)

        counts = collections.Counter()
        for vote_data in vote_data_list:
            counts[vote_data['option']] += 1
            vote.vote(**vote_data)

        for option, value in counts.items():
            vote.set_count(option, value)

        for source in sources:
            vote.add_source(**source)

        vote.extras.update(extras)

        return vote

    # ------------------------------------------------------------------------
    # Overridables
    # ------------------------------------------------------------------------
    @try_jxn_delegation
    def get_vote_result(self, value):
        '''
        '''
        raise NotImplemented()

    @try_jxn_delegation
    def get_vote_option(self, option_text):
        option_text = option_text.replace('-', ' ').lower()
        return self.cfg._BILL_VOTE_OPTION_MAP[option_text]

    @try_jxn_delegation
    def drop_organization(self, data):
        '''If this function returns True, the org is dropped.

        XXX: Right now, always drops the org.
        '''
        return data.pop('organization', None)

    @try_jxn_delegation
    def classify_motion_text(self, motion_text):
        '''Jurisdiction configs can override this to determine how
        vote motions will be classified.
        '''
        return []


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
            action = self.make_child(ActionAdapter, data).get_instance_data()
            yield action

    @make_item('sponsorships')
    def get_sponsorships(self):
        return self.data.get('sponsors', [])

    @make_item('votes', wrapwith=list)
    def gen_votes(self):
        for data in self.data.get('actions'):
            converter = self.make_child(VoteAdapter, data)
            more_data = dict(
                legislative_session=self.data['legislative_session'])
            vote = converter.get_instance(**more_data)
            if vote.votes:
                yield vote

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
            self.drop_action_organization(action)
            bill.add_action(**action)

        for sponsorship in data.pop('sponsorships'):
            if not self.should_drop_sponsor(sponsorship):
                kwargs = dict(
                    classification=self.get_sponsor_classification(sponsorship),
                    entity_type=self.get_sponsor_entity_type(sponsorship),
                    primary=self.get_sponsor_primary(sponsorship))
                kwargs.update(sponsorship)
                bill.add_sponsorship(**kwargs)

        for source in data.pop('sources'):
            bill.add_source(**source)

        bill.extras.update(data.pop('extras'))

        yield bill

        for vote in data.pop('votes'):
            vote.set_bill(bill)
            yield vote


    # ------------------------------------------------------------------------
    # Overridables: sponsorships
    # ------------------------------------------------------------------------
    @try_jxn_delegation
    def should_drop_sponsor(self, data):
        '''If this function retruns True, the sponsor is dropped.
        '''
        return False

    @try_jxn_delegation
    def get_sponsor_classification(self, data):
        '''Return the sponsor's pupa classification. Legistar generally
        doesn't provide any info like this, so we just return "".
        '''
        return 'sponsor'

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
    # Overridables: actions
    # ------------------------------------------------------------------------
    @try_jxn_delegation
    def drop_action_organization(self, data):
        '''
        XXX: This temporarily drops the action['organization'] from all
        actions. See pupa issue #105 https://github.com/opencivicdata/pupa/issues/105/

        When the organization is the top-level org, it doesn't get set
        on the action.
        '''
        data.pop('organization', None)

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
