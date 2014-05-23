'''
'''
import inspect

from legistar.views import LegistarScraper
from legistar.utils.itemgenerator import ItemGenerator, make_item
from legistar.utils.handythings import CachedAttr

import pupa.scrape


class PupaAdapter(ItemGenerator):
    '''Base class responsible for transforming legistar dict
    into dict suitable for invoking pupa models.
    '''
    def __init__(self, legistar_data):
        self.data = legistar_data

    def get_instance_data(self):
        # Collect the make_item output.
        self.data.update(self)

        # Apply the aliases.
        for oldkey, newkey in self.aliases:
            self.data[newkey] = self.data.pop(oldkey)

        # Drop non-pupa keys.
        for key in self.dropkeys:
            self.data.pop(key)

        return self.data

    def gen_argspecs(self):
        for cls in reversed(self.model.__mro__):
            yield inspect.getargspec(self.model)

    def get_instance(self):
        '''We can't pass compliant dicty objects into the pupa model
        constructors, so this hack passes the constructor data in, then
        manually setattr's all the remaining values.

        XXX: push this back into pupa
        '''
        instance_data = self.get_instance_data()

        # Aggregate all the positional args this model requires.
        args = {}
        for argspec in self.gen_argspecs():
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
        instance = self.model(**args)

        # Now add all other data. It must be in valid pupa form.
        for key in instance_data.keys() - args.keys():
            setattr(instance, key, instance_data[key])

        # Okeedoke, we're done.
        return instance


class PersonAdapter(PupaAdapter):
    '''Converts legistar data into a pupa.scrape.Person instance.
    Note the make_item methods are popping values out the dict,
    because the associated keys aren't valid pupa.scrape.Person fields.
    '''
    model = pupa.scrape.Legislator
    aliases = [('fullname', 'name'),]
    dropkeys = ['firstname', 'lastname', 'notes']

    @make_item('links', wrapwith=list)
    def get_links(self):
        website_url = self.data.pop('website', None)
        if website_url is not None:
            yield dict(note='website', url=website_url)

    @make_item('contact_details', wrapwith=list)
    def gen_contacts(self):
        email = self.data.pop('email', None)
        if email is not None:
            yield dict(type='email', value=email, note='')



class PupaConverter:
    '''Base class responsible for adding relations onto
    converted pupa instances using raw data obtained from
    a PupaAdapter instance. I fully realize/appreciate that
    all these classes are badly named.
    '''
    def __init__(self, legistar_data):
        self.data = legistar_data


class PersonConverter(PupaConverter):
    '''Cal get instance to
    '''
    adapter = PersonAdapter

    @property
    def committees(self):
        return self.generator.committees

    def get_committee(self, committee_name):
        '''Gets or creates the committee with name equal to
        kwargs['name']. Caches the result.
        '''
        committee = self.committees.get(committee_name)
        if committee is None:
            committee = pupa.scrape.Committee(name=committee_name)
            self.committees[committee_name] = committee
        return committee

    def create_membership(self, data, sources):
        '''Retrieves the matching committee and adds this person
        as a member of the committee.
        '''
        # Get or create the committee.
        committee_name = data.pop('org')
        committee = self.get_committee(committee_name)
        data['name_or_person'] = self.instance

        # Stringify the dates to comply with pupa.
        self.stringify_membership_dates(data)

        # Create the membership.
        committee.add_member(**data)

        # Add a source to the committee.
        for source in sources:
            if 'detail' in source['note']:
                committee.add_source(**source)

    def stringify_membership_dates(self, data):
        '''Mangle memberships to use stringy dates instead of dt dates.

        Note that this is safe to do here (i.e., we're tossing the time data)
        because people roles dont' typically have times associated, only
        dates. This wouldn't be safe on events.
        '''
        for date in 'start_date', 'end_date':
            dt = data.get(date)
            if dt is None:
                continue
            data[date] = dt.strftime('%Y-%m-%d')
        return data

    def get_instance(self):
        '''Creates the pupa Legislator instance, adds its memberships,
        and returns it.
        '''
        memberships = self.data.pop('memberships', [])
        sources = self.data.pop('sources', [])

        # Get the Person.
        self.instance = self.adapter(self.data).get_instance()

        # Add memberships.
        for membership_data in memberships:
            self.create_membership(membership_data, sources)

        # Add sources.
        self.instance.sources = sources
        return self.instance


class PupaGenerator:
    '''Instantiate this object with a list of pupatypes, then
    iterate over it to generate pupa objects. It invokes the
    legistar scraper and handles alias'ing the generic legistar
    field names over to valid pupa field names, then adds sources,
    links. etc.
    '''
    converters = dict(
        people=PersonConverter)

    models = dict(
        people=pupa.scrape.Legislator,
        committees=pupa.scrape.Committee,
        bills=pupa.scrape.Bill,
        events=pupa.scrape.Event)

    def __init__(self, *pupatypes):
        self.pupatypes = pupatypes
        self.committees = {}
        self.people = {}

    def __get__(self, inst, type_=None):
        self.inst = inst
        return self

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return self

    def __iter__(self):
        scraper = self.get_legistar_scraper()
        for pupatype in self.pupatypes:
            converter = self.converters[pupatype]
            converter.generator = self
            for data in scraper.gen_pupatype_data(pupatype):
                yield converter(data).get_instance()

        # Yield out any accumulated objects.
        yield from self.committees.values()
        yield from self.people.values()

    def get_legistar_scraper(self):
        div_id = self.inst.jurisdiction.division_id
        scraper = LegistarScraper.get_scraper(
            division_id=div_id,
            # Pass in the pupa scraper as requests client.
            session=self.inst)
        return scraper