import re

import pupa.scrape
from pupa.utils import make_psuedo_id

from legistar.utils.itemgenerator import make_item
from legistar.ext.pupa.base import Adapter, Converter, SetDefault
from legistar.jurisdictions.utils import try_jxn_delegation


class MembershipAdapter(Adapter):
    '''Convert a legistar scraper's membership into a pupa-compliant
    membership.
    '''
    pupa_model = pupa.scrape.Membership
    extras_keys = ['appointed_by']

    def stringify_date(self, dt):
        '''Given a datetime string, stringify it to a date,
        assuming there is no time portion associated with the date.
        Complain if there is.
        '''
        if dt is None:
            raise self.SkipItem()
        else:
            return dt.strftime('%Y-%m-%d')

    @make_item('start_date')
    def get_start_date(self):
        return self.stringify_date(self.data.get('start_date'))

    @make_item('end_date')
    def get_end_date(self):
        return self.stringify_date(self.data.get('end_date'))

    @make_item('organization_id')
    def get_org_id(self):
        return self.data['organization_id']

    def get_instance(self, **extra_instance_data):
        # Get instance data.
        instance_data = self.get_instance_data()
        instance_data.update(extra_instance_data)
        extras = instance_data.pop('extras')

        # Create the instance.
        instance = self.pupa_model(**instance_data)
        instance.extras.update(extras)
        return instance


class MembershipConverter(Converter):
    adapter = MembershipAdapter

    def __iter__(self):
        yield from self.create_memberships()

    def get_org(self, org_name):
        '''Gets or creates the org with name equal to
        kwargs['name']. Caches the result.
        '''
        created = False
        with SetDefault(self, 'orgs', {}) as orgs:
            # Get the org.
            org = orgs.get(org_name)

            if org is not None:
                # Cache hit.
                return created, org

            # Create the org.
            classification = self.cfg.get_org_classification(org_name)
            org = pupa.scrape.Organization(
                name=org_name, classification=classification)
            created = True

            # Cache it.
            orgs[org_name] = org

            # Add a source to the org.
            for source in self.person.sources:
                if 'detail' in source['note']:
                    org.add_source(**source)

        return created, org

    def create_membership(self, data):
        '''Retrieves the matching committee and adds this person
        as a member of the committee.
        '''
        if 'person_id' not in data:
            data['person_id'] = self.person._id

        # Get or create the committee.
        if 'organization_id' not in data:
            org_name = data.pop('org')
            created, org = self.get_org(org_name)
            if created:
                yield org

        # Add the person and org ids.
            data['organization_id'] = org._id

        # Convert the membership to pupa object.
        adapter = self.make_child(self.adapter, data)
        membership = adapter.get_instance()
        yield membership

    def create_memberships(self):
        # Yield the memberships found in the person's detail table.
        for membership in self.memberships:
            yield from self.create_membership(membership)

        # Also, if the person has a party, emit a party membership.
        if not self.party:
            return

        post_kwargs = {}
        post_kwargs['organization__classification'] = 'legislature'
        if self.district:
            post_kwargs['label'] = self.district

        membership = dict(
            person_id=self.person._id,
            organization_id=make_psuedo_id(classification="legislature"),
            post_id=make_psuedo_id(**post_kwargs),
            role='member',
            start_date=self.person._start_date,
            end_date=self.person._end_date)
        yield self.create_membership(membership)

        # create a party membership
        if self.party:
            membership = dict(
                person_id=self.person._id,
                organization_id=make_psuedo_id(
                    classification="party", name=self.party),
                role='member')
            yield self.create_membership(membership)


# ------------------------------------------------------------------------
# People
# ------------------------------------------------------------------------
class PeopleAdapter(Adapter):
    '''Converts legistar data into a pupa.scrape.Person instance.
    Note the make_item methods are popping values out the dict,
    because the associated keys aren't valid pupa.scrape.Person fields.
    '''
    pupa_model = pupa.scrape.Person
    aliases = [('fullname', 'name'),]
    extras_keys = ['firstname', 'lastname', 'notes']

    @make_item('links', wrapwith=list)
    def get_links(self):
        '''Move the website link into the pupa links attr,
        '''
        website_url = self.data.pop('website', None)
        if website_url is not None:
            yield dict(note='website', url=website_url)

    @make_item('contact_details', wrapwith=list)
    def gen_contacts(self):
        '''Move legistar's top-level email into contacts dict.
        '''
        for key in 'email', 'fax':
            email = self.data.pop(key, None)
            if email is not None:
                yield dict(type=key, value=email, note='')

        rename_keys = dict(phone='voice')

        # Addresses are a pain. This hacky garbage converts flat
        # address keys into a list of address objects.
        contact_keys = '''
            phone address address_city address_state address_zip
            '''.split()

        for officetype in ('district', 'city hall'):
            address = []
            office_key = officetype.replace(' ', '')
            note = officetype
            for contact_key in contact_keys:
                key = '%s_%s' % (office_key, contact_key)
                value = self.data.pop(key, None)
                if value is None:
                    continue
                if 'address' in contact_key:
                    address.append(value)
                else:
                    type_ = rename_keys.get(contact_key, contact_key)
                    yield dict(type=type_, value=value, note=officetype)

            if not address:
                continue

            # Yay! We got an address.
            address = '\n'.join([address[0], ' '.join(address[1:])])
            replace_func = lambda m: '%s,' % m.group(1)
            address = re.sub(r'([A-Z]{2})', replace_func, address)
            yield dict(type='address', value=address, note=officetype)

    def get_instance(self, **extra_instance_data):
        instance_data = self.get_instance_data(**extra_instance_data)
        instance = self.pupa_model(
            name=instance_data['name'],
            image=instance_data.get('image', ''))

        for key in ('links', 'sources', 'identifiers', 'contact_details'):
            helper_name = ('add_' + key).rstrip('s')
            helper = getattr(instance, helper_name)
            for data in instance_data.get(key):
                helper(**data)

        instance.extras.update(instance_data['extras'])
        return instance


class PeopleConverter(Converter):
    '''Invokes the person and membership adapters to output pupa Person
    objects.
    '''
    adapter = PeopleAdapter

    def gen_memberships(self):
        yield from self.make_child(MembershipConverter, self.memberships)

    def __iter__(self):
        '''Creates the pupa Legislator instance, adds its memberships,
        and returns it.
        '''
        # This sets this attrs to children can access them too.
        self.memberships = self.data.pop('memberships', [])
        self.party = self.data.pop('party', [])
        self.district = self.data.pop('district', [])

        # Get the Person.
        self.person = self.get_adapter().get_instance()

        # If a membership to the top-level org is given, steal the
        # start/end dates and nuke it.
        for i, memb in enumerate(self.memberships):
            if memb['org'] == self.cfg.TOPLEVEL_ORG_MEMBERSHIP_NAME_TEXT:
                self.person._start_date = memb.get('start_date')
                self.person._end_date = memb.get('end_date')
            self.memberships.pop(i)
            break

        yield self.person

        # Create memberships.
        yield from self.gen_memberships()
