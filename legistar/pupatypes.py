'''This module exposes metadata about pupa types.
'''
from legistar.utils.handythings import CachedAttr


PUPATYPES = VALID_PUPATYPES = ('events', 'orgs', 'people', 'bills')
VALID_VIEWTYPES = ('search', 'detail')
VALID_COMPONENT_TYPES = ('table',)
PUPATYPE_PREFIXES = ['EVT', 'ORG', 'PPL', 'BILL']


class InvalidPrefixValue(Exception):
    '''Raised if class specifies invalid prefix value.
    '''


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


class ConfigAttributeError(Exception):
    pass


class PupatypeMixin:

    # So subtypes don't have to import it.
    ConfigAttributeError = ConfigAttributeError

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
        raise NotImplemented(msg % self.__class__.__qualname__)

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
        raise NotImplemented(msg % self.__class__.__qualname__)

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
