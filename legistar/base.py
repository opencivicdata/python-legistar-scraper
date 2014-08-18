import re
import types
import inspect
import contextlib
import datetime
from collections import ChainMap

import pytz
import lxml.html

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

PUPATYPES = VALID_PUPATYPES = ('events', 'orgs', 'people', 'bills')
VALID_VIEWTYPES = ('search', 'detail')
VALID_COMPONENT_TYPES = ('table',)
PUPATYPE_PREFIXES = ['EVT', 'ORG', 'PPL', 'BILL']


class SettingsPrefix:

    def __init__(self, name, valid_set, parent=None, required=True):
        self.name = name
        self.valid_set = valid_set
        self.parent = parent
        self.required = required

    def __get__(self, inst, type_=None):
        self.inst = inst
        return self.get_prefix()

    def get_value(self):
        has_pupatype = self.inst.has_pupatype_inst
        value = getattr(has_pupatype, 'get_' + self.name.lower(), None)()
        if value is None and not self.required:
            return

        if value not in self.valid_set:
            msg = (
                '{0.__class__.__qualname__}.{1.name} must be one of '
                '{1.valid_set}, not {2!r}.')
            args = (has_pupatype, self, value)
            raise ValueError(msg.format(*args))
        return value

    def gen_inst_attrs(self):
        if self.parent is not None:
            yield from self.parent.gen_inst_attrs()
        yield self.get_value()

    def get_inst_attrs(self):
        return list(self.gen_inst_attrs())

    def get_prefix(self):
        return self.inst._mk_setting(*self.get_inst_attrs())


class TypePrefix(SettingsPrefix):
    _TYPE_PREFIXES = {
        'people': "PPL",
        'orgs': "ORG",
        'events': "EVT",
        'bills': "BILL",
    }
    def get_prefix(self):
        '''Get this pupatype's settings prefix.
        '''
        value = self.get_value()
        return self._TYPE_PREFIXES[value]

    def gen_inst_attrs(self):
        yield self.get_prefix()


class PupatypeAccessor:
    '''
    class Thing:
        VIEWTYPE = 'search'
        PUPATYPE = Pupatype('people')
        COMPONENT_TYPE = 'table'

    thing = Thing()
    print(thing.pupatype) --> 'people'
    print(thing.pupatype.type_prefix) --> 'PPL'
    print(thing.pupatype.view_prefix) --> 'PPL_SEARCH'
    print(thing.pupatype.prefix) --> 'PPL_SEARCH_TABLE'
    '''
    def __init__(self, has_pupatype_inst, pupatype):
        self.has_pupatype_inst = has_pupatype_inst
        self.name = pupatype
        for prefix_type in ('type', 'view', 'component'):
            getattr(self, '%s_prefix' % prefix_type)

    def _mk_setting(self, *parts):
        '''Get the name of a setting for this pupatype.
        '''
        return '_'.join(seg.upper() for seg in parts if seg is not None)

    type_prefix = TypePrefix('PUPATYPE', valid_set=VALID_PUPATYPES)
    view_prefix = SettingsPrefix(
        'VIEWTYPE', parent=type_prefix, valid_set=VALID_VIEWTYPES)
    component_prefix = SettingsPrefix(
        'COMPONENT_TYPE', parent=view_prefix, valid_set=VALID_COMPONENT_TYPES,
        required=False)


class Base:
    '''Lookups for these attributes on subtypes will fail over
    to whatever object's ChainMap the object's own ChainMap was derived
    from, and on up the chain, all the way back the jursdiction's config
    obj.
    '''
    SkipDocument = SkipDocument

    class ConfigAttributeError(Exception):
        pass

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

    def get_pupatype(self):
        '''Guess pupatype from the class name. If not guessable, complain.
        '''
        # Guess pupatype from class name.
        cls_name = self.__class__.__name__
        for pupatype in VALID_PUPATYPES:
            if pupatype in cls_name.lower():
                return pupatype
        # Complain.
        msg = '%s subtypes must include a pupatype, like People in the class name.'
        raise NotImplementedError(msg % self.__class__.__qualname__)

    def get_viewtype(self):
        '''Guess from the class name whether this is a search or detail
        view. If we're here, no VIEWTYPE was defined at the class level.
        '''
        # Guess viewtype from the class name.
        cls_name = self.__class__.__name__
        for viewtype in VALID_VIEWTYPES:
            if viewtype in cls_name.lower():
                return viewtype
        # Ok, complain.
        msg = '%s subtypes must include Search or Detail in the class name.'
        raise NotImplementedError(msg % self.__class__.__qualname__)

    def get_component_type(self):
        '''Guess from the class name whether this is a table component.
        If nothing is set, no prob.
        '''
        # Guess viewtype from the class name.
        cls_name = self.__class__.__name__
        for component_type in ('table',):
            if component_type in cls_name.lower():
                return component_type

    def get_prefixes(self):
        return PupatypeAccessor(self, self.get_pupatype())

    def get_pupatype_prefix(self):
        return self.get_prefixes().type_prefix

    def get_view_prefix(self):
        return self.get_prefixes().view_prefix

    def get_component_prefix(self):
        return self.get_prefixes().component_prefix

    def get_prefix(self):
        for prefix_type in ('component', 'view'):
            try:
                return getattr(self, 'get_%s_prefix' % prefix_type)()
            except AttributeError:
                continue
        return self.get_pupatype_prefix()

    def get_config_value(self, key):
        name = '%s_%s' % (self.get_prefix(), key.upper())
        try:
            return getattr(self.cfg, name)
        except AttributeError as exc:
            raise ConfigAttributeError(name) from exc

    def get_label_text(self, key):
        '''Get field label text using the class's prefix:

        self.get_label_text('topic') --> self.cfg.EVT_TABLE_TEXT_TOPIC
        '''
        key = 'TEXT_%s' % key.upper()
        return self.get_config_value(key)


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
