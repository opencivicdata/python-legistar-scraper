import re
import types
import inspect
import contextlib
import datetime
from collections import ChainMap

import pytz
import lxml.html

from legistar.pupatypes import PupatypeMixin
from legistar.base import Base, ChainedLookup
from legistar.views import LegistarScraper
from hercules import DictSetDefault

import pupa.scrape


class ChainedLookup:
    '''Wrapped values get lookup in the ancestor ChainMap objects. Setting
    this attributes sets the value in the instance's own ChainMap.
    '''
    def __init__(self, key):
        self.key = key

    def __get__(self, inst, owner=None):
        self.on_get(inst, owner)
        val = inst.chainmap.get(self.key)
        if val is None and hasattr(self, 'get_value'):
            val = self.get_value(inst, owner)
            inst.chainmap[self.key] = val
        return val

    def __set__(self, inst, value):
        self.on_set(inst, value)
        inst.chainmap[self.key] = value

    def on_get(self, inst, owner):
        '''Gets called before value is returned.
        '''
        pass

    def on_set(self, inst, value):
        '''Gets called before value is set.
        '''
        pass


class DocLookup(ChainedLookup):
    '''This one's expensive, so fetch it lazily and cache it.
    '''
    def get_value(self, inst, owner):
        # Blab.
        msg_args = (inst, inst.url)
        inst.debug('%s is fetching %s', *msg_args)

        # Fetch the page, parse.
        resp = inst.cfg.client.get(inst.url)
        doc = lxml.html.fromstring(resp.text)
        doc.make_links_absolute(inst.url)

        # Cache it and blab some more.
        inst.chainmap['doc'] = doc
        return doc

    def add_to_sources(self, inst, *args):
        '''Add the fetched web page to the parent object's chainmap.
        '''
        with DictSetDefault(inst.chainmap, 'sources', {}) as sources:
            sources[inst.sources_note] = inst.url

    # Add the url to sources when this doc gets used.
    on_get = on_set = add_to_sources


class ClientLookup(ChainedLookup):
    '''Getter for the client object. Doesn't create the client
    until it's accessed.
    '''
    def get_value(self, inst, owner):
        return inst.cfg.get_client()


class SessionLookup(ChainedLookup):
    '''Getter for the client object. Doesn't create the client
    until it's accessed.
    '''
    def get_value(self, inst, owner):
        return inst.cfg.get_session()


class SkipDocument(Exception):
    '''Raised when a condition encountered during scrape means this entire
    document is garbage that should be skipped.
    '''


class Base(PupatypeMixin):
    '''Lookups for these attributes on subtypes will fail over
    to whatever object's ChainMap the object's own ChainMap was derived
    from, and on up the chain, all the way back the jursdiction's config
    obj.
    '''
    SkipDocument = SkipDocument

    # The jxn config object.
    config = config_obj = cfg = ChainedLookup('config')
    url = ChainedLookup('url')
    # The lxml.htm doc.
    doc = DocLookup('doc')
    # The config's requests.Session and Scraper object.
    client = ClientLookup('client')
    session = SessionLookup('session')

    # Logging methods.
    info = ChainedLookup('info')
    debug = ChainedLookup('debug')
    warn = warning = ChainedLookup('warning')
    critical = ChainedLookup('critical')
    error = ChainedLookup('error')
    exception = ChainedLookup('exception')

    @property
    def firefox(self):
        from legistar import selenium_client
        return selenium_client.browser

    @property
    def chainmap(self):
        '''This property manages the instance's ChainMap objects.
        '''
        chainmap = getattr(self, '_chainmap', None)
        if chainmap is not None:
            return chainmap
        else:
            chainmap = ChainMap()
            self._chainmap = chainmap
            return chainmap

    @chainmap.setter
    def chainmap(self, chainmap):
        self._chainmap = chainmap

    def set_parent_chainmap(self, chainmap):
        '''Set `chainmap` as the parent of self.chainmap.
        '''
        self.chainmap = ChainMap(self.chainmap.maps[0], *chainmap.maps)

    def provide_chainmap_to(self, has_child_chainmap):
        '''Set self.chainmap as the parent of child's chainmap.
        '''
        has_child_chainmap.set_parent_chainmap(self.chainmap)
        return has_child_chainmap

    def inherit_chainmap_from(self, has_parent_chainmap):
        '''Set this object as the chainmap parent of has_child_chainmap.
        '''
        self.set_parent_chainmap(has_parent_chainmap.chainmap)
        return has_parent_chainmap

    def make_child(self, child_type, *child_args, **child_kwargs):
        '''Invoke the passed in type with the args/kwargs, then provide
        self.chainmap to it, basically making it a child context.
        '''
        child = child_type(*child_args, **child_kwargs)
        return self.provide_chainmap_to(child)


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
