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


# ---------------------------------------------------------------------------
# Functions for selectively overriding arbitrary scraping
# methods by marking a replacement function on the jxn config.
# ---------------------------------------------------------------------------
def overrides(clsname_membername_spec):
    '''Decorator used to mark a config method as intended to
    override one of the methods defined on the stock scraping
    classes. Use like:

    class MyJxn(Config):
        ...
        @overrides('BillSearchForm.get_query')
        def custom_query(self):
            ...

    The ovverriden method, BillSearchForm.get_query, is wrapped
    with a try_jxn_delegation decorator that will check the jxn config
    for an override function and run it before allowing the default
    to run.
    '''
    def decorator(f):
        clsname, membername = clsname_membername_spec.split('.')
        f._is_override = True
        f._override_clsname = clsname
        f._override_membername = membername
        return f
    return decorator


def try_jxn_delegation(func):
    '''The above-referenced decorator, which marks a function as needing
    to check first whether an override has been defined on the jxn config.
    '''
    def f(self, *args, _overriden_func=func, **kwargs):
        # Check whether the function has an override registered.
        func = _overriden_func
        cls_name = self.__class__.__name__
        if cls_name in self.cfg.override_funcs:
            funcs = self.cfg.override_funcs[cls_name]
            funcname = func.__name__
            if funcname in funcs:
                return funcs[funcname](self, *args, **kwargs)
        # Otherwise run the default function.
        return func(self, *args, **kwargs)
    return f
