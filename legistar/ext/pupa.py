'''
'''
import re
import inspect

from legistar.base import Base, ChainedLookup
from legistar.views import LegistarScraper
from legistar.utils.itemgenerator import ItemGenerator, make_item
from legistar.utils.handythings import CachedAttr, DictSetDefault, SetDefault

import pupa.scrape
from pupa.utils import make_psuedo_id


class PupaExtBase(Base):
    '''This class's attrs are inherited state values. If they are defined in
    an object's parent chainmap, the object can get/set them. Get's will
    occur on ancestor chainmaps; gets happen in the instances own map
    and don't affect ancestors.
    '''
    # ------------------------------------------------------------------------
    # Names set on the generator and availabe to its children:
    # ------------------------------------------------------------------------

    # The main organization, like City Council (i.e., not "Cow Subcommittee")
    top_level_org = ChainedLookup('top_level_org')
    # The main generator (the object invoked by pupa). Will be the
    # parent chainmap of all other PupaExtBase types used in the module.
    generator = ChainedLookup('generator')
    # Cache of orgs; maps org names to instances.
    orgs = ChainedLookup('orgs')

    # ------------------------------------------------------------------------
    # Names set on the person converter and availabe to its children:
    # ------------------------------------------------------------------------
    # The current person being imported and similar:
    person = ChainedLookup('person')
    sources = ChainedLookup('sources')
    memberships = ChainedLookup('memberships')
    party = ChainedLookup('party')
    district = ChainedLookup('district')


class PupaAdapter(PupaExtBase, ItemGenerator):
    '''Base class responsible for mutating legistar dict
    into dict suitable for invoking pupa models.
    '''
    # The pupa_model the transormed pupa data will be used to invoke.
    pupa_model = None
    # List of (old_key, new_key) pairs used to rename fields.
    aliases = []
    # Values at these keys will be moved into the extras dict.
    extras_keys = []

    def __init__(self, legistar_data, *args, **kwargs):
        self.data = legistar_data
        self.args = args
        self.kwargs = kwargs

    def get_instance_data(self):
        '''Converts legistar dict output into data suitable for
        pupa.scrape pupa_model invocation. For example, datetimes need to
        be stringified. Based on class-level properties, dict items
        will be renamed, overwritten, or moved into `extras`. Mutates
        the legistar dict in place.
        '''
        # Collect the make_item output.
        self.data.update(self)

        # Apply the aliases.
        for oldkey, newkey in self.aliases:
            self.data[newkey] = self.data.pop(oldkey)

        # Move non-pupa keys into the extras dict.
        with DictSetDefault(self.data, 'extras', {}) as extras:
            for key in self.extras_keys:
                value = self.data.pop(key, None)
                if value is not None:
                    extras[key] = value
        return self.data

    def _gen_argspecs(self):
        '''Collects all argspecs for the objects __mro__, to make sure
        all required ars are getting passed.
        '''
        for cls in reversed(self.pupa_model.__mro__):
            yield inspect.getargspec(self.pupa_model)

    def get_instance(self):
        '''We can't pass compliant dicty objects into the pupa pupa_model
        constructors, so this hack passes the constructor data in, then
        manually setattr's all the remaining values.

        XXX: push this back into pupa?
        '''
        instance_data = self.get_instance_data()

        # Aggregate all the positional args this pupa_model requires.
        args = {}
        for argspec in self._gen_argspecs():
            for argname in argspec.args:
                if argname == 'self':
                    continue
                if argname in args:
                    continue
                value = instance_data.get(argname)

                # If the value is none, ditch it in favor of whatever
                # defaults may be defined.
                if not value:
                    instance_data.pop(argname, None)
                    continue

                # Store the arg value.
                args[argname] = value

        # Create the bare-bones instance.
        instance = self.pupa_model(**args)

        # Now add all other data. It must be in valid pupa form.
        for key in instance_data.keys() - args.keys():
            setattr(instance, key, instance_data[key])

        # Okeedoke, we're done.
        return instance


class MembershipAdapter(PupaAdapter):
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
        '''If the org is the top-level org, create a psuedo_id similar
        to the one found in pupa.scrape.helpers. I mindlessly copied
        this, so it might be wrong.
        '''
        if self.data['organization_id'] == self.top_level_org._id:
            # XXX: This might be wrong.
            msg = "Creating pseudo_id for %s's membership in %s."
            self.warning(msg, self.person.name, self.top_level_org.name)
            return make_psuedo_id(classification="legislature")
        return self.data['organization_id']


class PersonAdapter(PupaAdapter):
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
            address = '\n'.join([address[0], ' '.join(address[1:])])
            replace_func = lambda m: '%s,' % m.group(1)
            address = re.sub(r'([A-Z]{2})', replace_func, address)
            yield dict(type='address', value=address, note=officetype)


class PupaConverter(PupaExtBase):
    '''Base class responsible for adding relations onto
    converted pupa instances using raw data obtained from
    a PupaAdapter instance. I fully realize/appreciate that
    all these classes are badly named.
    '''
    def __init__(self, legistar_data):
        self.data = legistar_data

    def get_adapter(self, data=None):
        return self.make_child(self.adapter, data or self.data)

    def get_instance(self, data=None):
        return self.get_adapter(data).get_instance()


class MembershipConverter(PupaConverter):
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
                # Hache hit.
                return created, org

            # Create the org.
            org = pupa.scrape.Organization(name=org_name)
            created = True

            # Store the council, if this is a council membership.
            if org_name == self.cfg.TOPLEVEL_ORG_MEMBERSHIP_NAME_TEXT:
                self.generator.set_toplevel_org(org)

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
        # Get or create the committee.
        org_name = data.pop('org')
        created, org = self.get_org(org_name)
        if created:
            yield org

        # Add the person and org ids.
        data.update(
            person_id=self.person._id,
            organization_id=org._id)

        # Convert the membership to pupa object.
        membership = self.get_instance(data)
        yield membership

    def create_memberships(self):
        # Yield the memberships found in the person's detail table.
        for membership in self.memberships:
            yield from self.create_membership(membership)

        # Also, if the person has a party, emit a party membership.
        if not self.party:
            return
        yield self.adapter.pupa_model(
            self.person._id,
            make_psuedo_id(classification="party", name=self.party),
            role='member')


class PersonConverter(PupaConverter):
    '''Invokes the person and membership adapters to output pupa Person
    objects.
    '''
    adapter = PersonAdapter

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
        yield self.person

        # Create memberships.
        yield from self.gen_memberships()


class PupaGenerator(PupaExtBase):
    '''Instantiate this object with a list of pupatypes, then
    iterate over it to generate pupa objects. It invokes the
    legistar scraper and handles alias'ing the generic legistar
    field names over to valid pupa field names, then adds sources,
    links. etc.
    '''
    converter_types = dict(
        people=PersonConverter)

    def __init__(self, *pupatypes):
        self.pupatypes = pupatypes

    def __get__(self, inst, type_=None):
        self.inst = inst
        return self

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return self

    def __iter__(self):
        scraper = self.get_legistar_scraper()
        self.orgs = {}

        for pupatype in self.pupatypes:
            # Get the corresponding converter type.
            converter_type = self.converter_types[pupatype]
            for data in scraper.gen_pupatype_data(pupatype):
                # For each type, create a converter that inherits self's
                # chainmap.
                converter = self.make_child(converter_type, data)
                # And get the converted pupa instance.
                yield from converter

        # Yield out any accumulated objects.
        yield from self.orgs.values()

    def get_legistar_scraper(self):
        '''Get the owner instance's jurisdiction and retrieve the
        corresponding scraper. Inherit its chainmap.
        '''
        div_id = self.inst.jurisdiction.division_id
        scraper = LegistarScraper.get_scraper(
            division_id=div_id,
            # Pass in the pupa scraper as requests client.
            session=self.inst)

        # Inherit the jurisdiction's chainmap!
        scraper.config.provide_chainmap_to(self)
        # So children can access the generator.
        self.chainmap['generator'] = self

        return scraper

    def set_toplevel_org(self, org):
        '''Make the top-level org available to child types so they can
        auto-create a membership for each person in it.
        '''
        self.top_level_org = org

# ----------------------------------------------------------------------------
# Importables
# ----------------------------------------------------------------------------
class LegistarPeopleScraper(pupa.scrape.Scraper):
    # This also scrapes orgs.
    scrape = PupaGenerator('people')
