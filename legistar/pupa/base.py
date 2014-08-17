import re
import types
import inspect
import datetime

from legistar.base import Base, ChainedLookup
from legistar.views import LegistarScraper
from hercules import DictSetDefault

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


class Adapter(PupaExtBase):
    '''Base class responsible for mutating legistar dict
    into dict suitable for invoking pupa models.
    '''
    # The pupa_model the transormed pupa data will be used to invoke.
    pupa_model = None
    # List of (old_key, new_key) pairs used to rename fields.
    aliases = []
    # Values at these keys will be moved into the extras dict.
    extras_keys = []
    # Values at these keys get dropped.
    drop_keys = []

    def __init__(self, legistar_data, *args, **kwargs):
        self.data = legistar_data
        self.args = args
        self.kwargs = kwargs

    def get_instance_data(self, **extra_instance_data):
        '''Converts legistar dict output into data suitable for
        pupa.scrape pupa_model invocation. For example, datetimes need to
        be stringified. Based on class-level properties, dict items
        will be renamed, overwritten, or moved into `extras`. Mutates
        the legistar dict in place.
        '''
        data = dict(self.data)
        data.update(extra_instance_data)

        # Collect the make_item output.
        data.update(self)

        # Apply the aliases.
        for oldkey, newkey in self.aliases:
            data[newkey] = data.pop(oldkey)

        # Move non-pupa keys into the extras dict.
        with DictSetDefault(data, 'extras', {}) as extras:
            for key in self.extras_keys:
                value = data.pop(key, None)
                if value is not None:
                    extras[key] = value

        # Drop keys.
        for key in self.drop_keys:
            data.pop(key, None)

        return data

    def _gen_argspecs(self):
        '''Collects all argspecs for the objects __mro__, to make sure
        all required ars are getting passed.
        '''
        for cls in reversed(self.pupa_model.__mro__):
            yield inspect.getfullargspec(self.pupa_model)

    def get_instance(self, **extra_instance_data):
        '''The only supported way to create pupa objects is through the
        python package, so subclasses must define this method.
        '''
        raise NotImplementedError()


class Converter(PupaExtBase):
    '''Base class responsible for adding relations onto
    converted pupa instances using raw data obtained from
    a PupaAdapter instance. I fully realize/appreciate that
    all these classes are badly named.
    '''
    def __init__(self, legistar_data):
        self.data = legistar_data

    def __iter__(self):
        data = self.get_adapter().get_instance()

        # This allows adapters to return None from get_instance
        # as a way of dropping data that shoulnd't make it into pupa.
        if not data:
            return

        if isinstance(data, types.GeneratorType):
            yield from data
        else:
            yield data

    def get_adapter(self, data=None):
        return self.make_child(self.adapter, data or self.data)
