import re
import inspect
import datetime

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


class Adapter(PupaExtBase, ItemGenerator):
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

        import pprint
        pprint.pprint(instance_data)
        print('*' * 30)
        pprint.pprint(instance.as_dict())
        import pdb; pdb.set_trace()

        # Okeedoke, we're done.
        return instance


class Converter(PupaExtBase):
    '''Base class responsible for adding relations onto
    converted pupa instances using raw data obtained from
    a PupaAdapter instance. I fully realize/appreciate that
    all these classes are badly named.
    '''
    def __init__(self, legistar_data):
        self.data = legistar_data

    def __iter__(self):
        '''Creates the pupa Legislator instance, adds its memberships,
        and returns it.
        '''
        # Get the Person.
        yield self.get_adapter().get_instance()

    def get_adapter(self, data=None):
        return self.make_child(self.adapter, data or self.data)

    def get_instance(self, data=None):
        return self.get_adapter(data).get_instance()

