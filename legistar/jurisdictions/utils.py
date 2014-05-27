from collections import namedtuple
from legistar.pupatypes import PUPATYPES, PUPATYPE_PREFIXES


def resolve_name(name, module_name=None, raise_exc=True):
    '''Given a name string and module prefix, try to import the name.
    '''
    if not isinstance(name, str):
        return name
    if module_name is None:
        module_name, _, name = name.rpartition('.')
    try:
        module = __import__(module_name, globals(), locals(), [name], 0)
    except ImportError:
        if raise_exc:
            raise
    else:
        return getattr(module, name)


class Tabs:
    '''Desceriptor to help in aggregating TAB* metadata on jxn config types.
    '''
    TabItemMeta = namedtuple('TabMeta', 'path, pupatype')

    def __get__(self, inst, type_=None):
        self.inst = inst
        return self

    def _gen_tabs(self):
        for pupatype in PUPATYPE_PREFIXES:
            data = getattr(self.inst, pupatype + '_TAB_META')
            yield self.TabItemMeta(*data)

    def get_by_pupatype(self, pupatype):
        for tab in self._gen_tabs():
            if pupatype == tab.pupatype:
                return tab


class Mimetypes:
    '''The fact that this class exists just proves that opening up
    government data is really important. All it does is aggregate the
    MIMETYPE_GIF_ settings and convert them to a dict that relates
    gif urls to mimetypes.
    '''
    def __get__(self, inst, type_=None):
        self.inst = inst
        return dict(self._gen_items(inst))

    def _gen_items(self, inst):
        prefixes = ('MIMETYPE_GIF_', 'MIMETYPE_EXT_')
        for name in dir(inst):
            for prefix in prefixes:
                if name.startswith(prefix):
                    yield getattr(inst, name)


_viewmeta_fields = (
    'pupatype',
    'form', 'table', 'tablerow', 'tablecell', 'view')

# ViewTypeMeta = namedtuple('_ViewTypeMeta', _viewmeta_fields)


class ViewType(namedtuple('ViewType', _viewmeta_fields)):
    '''Holds metadata about a view available on the site.
    '''

    def _resolve_qualname(self, qualname):
        module_name, classname = qualname.rsplit('.', 1)
        return resolve_name(classname, module_name=module_name)

    @property
    def Form(self):
        return self._resolve_qualname(self.form)

    @property
    def Table(self):
        return self._resolve_qualname(self.table)

    @property
    def TableRow(self):
        return self._resolve_qualname(self.tablerow)

    @property
    def TableCell(self):
        return self._resolve_qualname(self.tablecell)

    @property
    def View(self):
        return self._resolve_qualname(self.view)


class Views:
    '''Holds information about views available on the site;
    makes the info accessible by pupatype from the jxn's config.
    '''
    ViewMeta = namedtuple('_ViewMetaBase', 'pupatype search detail')

    def __get__(self, inst, type_=None):
        self.inst = inst
        return self

    def _gen_types(self, suffix):
        for pupatype in PUPATYPE_PREFIXES:
            yield getattr(self.inst, pupatype + suffix)

    def _gen_types_search_Form(self):
        yield from self._gen_types('_SEARCH_FORM_CLASS')

    def _gen_types_search_Table(self):
        yield from self._gen_types('_SEARCH_TABLE_CLASS')

    def _gen_types_search_TableRow(self):
        yield from self._gen_types('_SEARCH_TABLEROW_CLASS')

    def _gen_types_search_TableCell(self):
        yield from self._gen_types('_SEARCH_TABLECELL_CLASS')

    def _gen_types_search_View(self):
        yield from self._gen_types('_SEARCH_VIEW_CLASS')

    def _gen_types_detail_Form(self):
        yield from self._gen_types('_DETAIL_FORM_CLASS')

    def _gen_types_detail_Table(self):
        yield from self._gen_types('_DETAIL_TABLE_CLASS')

    def _gen_types_detail_TableRow(self):
        yield from self._gen_types('_DETAIL_TABLEROW_CLASS')

    def _gen_types_detail_TableCell(self):
        yield from self._gen_types('_DETAIL_TABLECELL_CLASS')

    def _gen_types_detail_View(self):
        yield from self._gen_types('_DETAIL_VIEW_CLASS')

    def _gen_meta(self):
        search_meta = zip(
            PUPATYPES,
            self._gen_types_search_Form(),
            self._gen_types_search_Table(),
            self._gen_types_search_TableRow(),
            self._gen_types_search_TableCell(),
            self._gen_types_search_View(),
            )
        detail_meta = zip(
            PUPATYPES,
            self._gen_types_detail_Form(),
            self._gen_types_detail_Table(),
            self._gen_types_detail_TableRow(),
            self._gen_types_detail_TableCell(),
            self._gen_types_detail_View(),
            )

        iterables = PUPATYPES, search_meta, detail_meta
        for pupatype, searchmeta, detailmeta in zip(*iterables):
            searchmeta = ViewType._make(searchmeta)
            detailmeta = ViewType._make(detailmeta)
            meta = self.ViewMeta(
                pupatype=pupatype,
                search=searchmeta,
                detail=detailmeta)
            yield meta

    def get_by_pupatype(self, pupatype):
        for meta in self._gen_meta():
            if pupatype == meta.pupatype:
                return meta
        msg = (
            'No viewmeta found for pupatype %r. '
            'Available pupatypes are %r')
        types = [meta.pupatype for meta in self._gen_meta()]
        raise Exception(msg % (pupatype, types))


# ----------------------------------------------------------------------------
# This stuff is probably pointless garbage.
# ----------------------------------------------------------------------------
class SettingsNode:
    '''Empty container class for nesty settings.
    '''
    def __init__(self, nodename=None, parent=None):
        self._nodename = nodename
        self._parent = parent
        self._names = set()

    def __iter__(self):
        for name in self._names:
            yield getattr(self, name)

    def __repr__(self):
        args = (self.__class__.__qualname__, self._qualname())
        return '%s(%r)' % args

    def _qualname(self):
        segs = [self._nodename or '']
        this = self
        while this._parent is not None:
            parent = this._parent
            segs.append(parent._nodename or '')
            this = parent
        return '.'.join(filter(None, segs[::-1]))

    def _get_child(self, nodename):
        child = getattr(self, nodename, None)
        if child is None:
            child = SettingsNode(nodename)
            child._parent = self
            setattr(self, nodename, child)
        return child

    def set_value(self, name, value):
        self._names.add(name)
        setattr(self, name, value)


class SettingsAccessor:
    '''Descriptor that compiles ALL_CAPS settings on config objs and
    makes them available with lowercase dot notation.
    '''
    def __get__(self, inst, type=None):
        settings = getattr(self, 'settings', None)
        if settings is None:
            settings = self.compile_settings(inst)
        return settings

    @property
    def settings(self):
        return getattr(self, '_settings', None)

    @settings.setter
    def settings(self, value):
        self._settings = value

    def compile_settings(self, inst):
        settings = SettingsNode()
        for name in dir(inst):
            if not name.isupper():
                continue
            value = getattr(inst, name)
            self.add_setting(settings, name, value)
        return settings

    def add_setting(self, settings, name, value):
        segs = name.lower().split('_')
        last_seg = segs.pop()
        this = settings
        for seg in segs:
            this = this._get_child(seg.lower())
        this.set_value(last_seg, value)

