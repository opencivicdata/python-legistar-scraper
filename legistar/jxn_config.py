from urllib.parse import urlparse
from collections import namedtuple, ChainMap

import requests
from hercules import CachedAttr

from legistar.client import Client
from legistar.base.ctx import CtxMixin


PUPATYPES = ('events', 'orgs', 'people', 'bills')
PUPATYPE_PREFIXES = [s.upper() for s in PUPATYPES]


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


class TabMeta:

    def __get__(self, inst, type_=None):
        self.inst = inst
        return self

    def _gen_tabs(self):
        for pupatype in PUPATYPE_PREFIXES:
            yield getattr(self.inst, pupatype + '_TAB_META')

    def get_by_pupatype(self, pupatype):
        for tab in self._gen_tabs():
            if pupatype == tab.pupatype:
                return tab

    def get_by_text(self, tabtext):
        for tab in self._gen_tabs():
            if tabtext == tab.text:
                return tab


_viewmeta_fields = (
    'pupatype',
    'form', 'table', 'tablerow', 'tablecell', 'view')

ViewMeta = namedtuple('_ViewMetaBase', 'pupatype search detail')
ViewTypeMeta = namedtuple('_ViewTypeMeta', _viewmeta_fields)


class ViewTypeMeta(ViewTypeMeta):
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


class ViewsMeta:
    '''Holds information about views available on the site;
    makes the info accessible by pupatype from the jxn's config.
    '''
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
            searchmeta = ViewTypeMeta._make(searchmeta)
            detailmeta = ViewTypeMeta._make(detailmeta)
            meta = ViewMeta(
                pupatype=pupatype,
                search=searchmeta,
                detail=detailmeta)
            yield meta

    def get_by_pupatype(self, pupatype):
        for meta in self._gen_meta():
            if pupatype == meta.pupatype:
                return meta


JXN_CONFIGS = {}


class ConfigMeta(type):
    def __new__(meta, name, bases, attrs):
        cls = type.__new__(meta, name, bases, attrs)
        root_url = attrs.get('root_url')
        if root_url is not None:
            data = urlparse(cls.root_url)
            JXN_CONFIGS[data.netloc] = cls
        ocd_id = attrs.get('ocd_id')
        if ocd_id is not None:
            JXN_CONFIGS[ocd_id] = cls

        return cls


class Config(CtxMixin, metaclass=ConfigMeta):

    SESSION_CLASS = requests.Session

    # Preceding slashes are necessary
    MIMETYPE_GIF_PDF = '/Images/PDF.gif'
    # MIMETYPE_GIF_VIDEO = '/Images/PDF.gif'

    TAB_TEXT_ID = 'ctl00_tabTop'
    TAB_TEXT_XPATH_TMPL = 'string(//div[@id="%s"]//a[contains(@class, "rtsSelected")])'
    TAB_TEXT_XPATH = TAB_TEXT_XPATH_TMPL % TAB_TEXT_ID

    # These are config options that can be overridden.
    tabs = TabMeta()
    TabItemMeta = namedtuple('TabMeta', 'path, text, pupatype')
    EVENTS_TAB_META = TabItemMeta('Calendar.aspx', 'Calendar', 'events')
    ORGS_TAB_META = TabItemMeta('Departments.aspx', 'Committees', 'orgs')
    BILLS_TAB_META = TabItemMeta('Legislation.aspx', 'Legislation', 'bills')
    PEOPLE_TAB_META = TabItemMeta('MainBody.aspx', 'City Council', 'people')

    # Url paths.
    EVENT_DETAIL_PATH = 'MeetingDetail.aspx'
    ORG_DETAIL_PATH = 'DepartmentDetail.aspx'

    # Pagination.
    PGN_CURRENT_PAGE_TMPL = '//*[contains(@class, "%s")]'
    PGN_CURRENT_PAGE_CLASS = 'rgCurrentPage'
    PGN_CURRENT_PAGE_XPATH = PGN_CURRENT_PAGE_TMPL % PGN_CURRENT_PAGE_CLASS
    PGN_NEXT_PAGE_TMPL = '%s/following-sibling::a[1]'
    PGN_NEXT_PAGE_XPATH = '%s/following-sibling::a[1]' % PGN_CURRENT_PAGE_XPATH

    # XXX lazy loading stuff good here?
    viewmeta = ViewsMeta()
    EVENTS_SEARCH_VIEW_CLASS = 'legistar.events.search.view.SearchView'
    EVENTS_DETAIL_VIEW_CLASS = 'legistar.events.detail.view.DetailView'
    EVENTS_SEARCH_TABLE_CLASS = 'legistar.events.search.table.Table'
    EVENTS_SEARCH_TABLEROW_CLASS = 'legistar.events.search.table.TableRow'
    EVENTS_SEARCH_TABLECELL_CLASS = 'legistar.base.table.TableCell'
    EVENTS_SEARCH_FORM_CLASS = 'legistar.events.search.form.Form'
    EVENTS_DETAIL_TABLE_CLASS = 'legistar.events.detail.table.Table'
    EVENTS_DETAIL_TABLEROW_CLASS = 'legistar.events.detail.table.TableRow'
    EVENTS_DETAIL_TABLECELL_CLASS = 'legistar.base.table.TableCell'
    EVENTS_DETAIL_FORM_CLASS = 'legistar.events.detail.form.Form'

    ORGS_SEARCH_VIEW_CLASS = 'legistar.orgs.search.view.SearchView'
    ORGS_DETAIL_VIEW_CLASS = 'legistar.orgs.detail.view.DetailView'
    ORGS_SEARCH_TABLE_CLASS = 'legistar.orgs.search.table.Table'
    ORGS_SEARCH_TABLEROW_CLASS = 'legistar.orgs.search.table.TableRow'
    ORGS_SEARCH_TABLECELL_CLASS = 'legistar.base.table.TableCell'
    ORGS_SEARCH_FORM_CLASS = 'legistar.orgs.search.form.Form'
    ORGS_DETAIL_TABLE_CLASS = 'legistar.orgs.detail.table.Table'
    ORGS_DETAIL_TABLEROW_CLASS = 'legistar.orgs.detail.table.TableRow'
    ORGS_DETAIL_TABLECELL_CLASS = 'legistar.base.table.TableCell'
    ORGS_DETAIL_FORM_CLASS = 'legistar.orgs.detail.form.Form'

    PEOPLE_SEARCH_VIEW_CLASS = 'legistar.people.search.view.SearchView'
    PEOPLE_DETAIL_VIEW_CLASS = 'legistar.people.detail.view.DetailView'
    PEOPLE_SEARCH_TABLE_CLASS = 'legistar.people.search.table.Table'
    PEOPLE_SEARCH_TABLEROW_CLASS = 'legistar.people.search.table.TableRow'
    PEOPLE_SEARCH_TABLECELL_CLASS = 'legistar.base.table.TableCell'
    PEOPLE_SEARCH_FORM_CLASS = 'legistar.people.search.form.Form'
    PEOPLE_DETAIL_TABLE_CLASS = 'legistar.people.detail.table.Table'
    PEOPLE_DETAIL_TABLEROW_CLASS = 'legistar.people.detail.table.TableRow'
    PEOPLE_DETAIL_TABLECELL_CLASS = 'legistar.base.table.TableCell'
    PEOPLE_DETAIL_FORM_CLASS = 'legistar.people.detail.form.Form'

    BILLS_SEARCH_VIEW_CLASS = 'legistar.bills.search.view.SearchView'
    BILLS_DETAIL_VIEW_CLASS = 'legistar.bills.detail.view.DetailView'
    BILLS_SEARCH_TABLE_CLASS = 'legistar.bills.search.table.Table'
    BILLS_SEARCH_TABLEROW_CLASS = 'legistar.bills.search.table.TableRow'
    BILLS_SEARCH_TABLECELL_CLASS = 'legistar.base.table.TableCell'
    BILLS_SEARCH_FORM_CLASS = 'legistar.bills.search.form.Form'
    BILLS_DETAIL_TABLE_CLASS = 'legistar.bills.detail.table.Table'
    BILLS_DETAIL_TABLEROW_CLASS = 'legistar.bills.detail.table.TableRow'
    BILLS_DETAIL_TABLECELL_CLASS = 'legistar.base.table.TableCell'
    BILLS_DETAIL_FORM_CLASS = 'legistar.bills.detail.form.Form'

    NO_RECORDS_FOUND_TEXT = 'No records were found'
    RESULTS_TABLE_XPATH = '//table[contains(@class, "rgMaster")]'

    # ------------------------------------------------------------------------
    # Events config
    # ------------------------------------------------------------------------
    EVENTS_DEFAULT_TIME_PERIOD = 'This Year'
    EVENTS_DEFAULT_BODIES = 'All Committees'
    EVENTS_BODIES_EL_NAME = 'ctl00$ContentPlaceHolder1$lstBodies'
    EVENTS_TIME_PERIOD_EL_NAME = 'ctl00$ContentPlaceHolder1$lstYears'

    # ------------------------------------------------------------------------
    # Events table config.
    EVT_TABLE_TEXT_NAME = 'Name'
    EVT_TABLE_TEXT_DATE =  'Meeting Date'
    EVT_TABLE_TEXT_ICAL =  ''
    EVT_TABLE_TEXT_TIME = 'Meeting Time'
    EVT_TABLE_TEXT_LOCATION = 'Meeting Location'
    EVT_TABLE_TEXT_TOPIC = 'Meeting Topic'
    EVT_TABLE_TEXT_DETAILS = 'Meeting Details'
    EVT_TABLE_TEXT_AGENDA = 'Agenda'
    EVT_TABLE_TEXT_MINUTES = 'Minutes'
    EVT_TABLE_TEXT_MEDIA = 'Multimedia'
    EVT_TABLE_TEXT_NOTICE = 'Notice'

    EVT_TABLE_DATETIME_FORMAT = '%m/%d/%Y %I:%M %p'

    EVT_TABLE_PUPA_KEY_NAME = EVT_TABLE_TEXT_TOPIC
    EVT_TABLE_PUPA_KEY_LOCATION = EVT_TABLE_TEXT_LOCATION

    EVT_TABLE_PUPA_PARTICIPANTS = {
        'organization': [EVT_TABLE_TEXT_NAME]
        }

    EVT_TABLE_PUPA_DOCUMENTS = [
        EVT_TABLE_TEXT_AGENDA,
        EVT_TABLE_TEXT_MINUTES,
        EVT_TABLE_TEXT_NOTICE,
        ]

    # ------------------------------------------------------------------------
    # Events detail config.
    EVT_DETAIL_TEXT_NAME = EVT_TABLE_TEXT_NAME
    EVT_DETAIL_TEXT_TOPIC = EVT_TABLE_TEXT_TOPIC
    EVT_DETAIL_TEXT_DETAILS = EVT_TABLE_TEXT_DETAILS
    EVT_DETAIL_TEXT_MEDIA = EVT_TABLE_TEXT_MEDIA
    EVT_DETAIL_TEXT_NOTICE = EVT_TABLE_TEXT_NOTICE
    EVT_DETAIL_TEXT_LOCATION = 'Meeting location'
    EVT_DETAIL_TEXT_DATE = 'Date'
    EVT_DETAIL_TEXT_TIME = 'Time'
    EVT_DETAIL_TEXT_VIDEO = 'Meeting video'
    EVT_DETAIL_TEXT_AGENDA = 'Published agenda'
    EVT_DETAIL_TEXT_AGENDA_STATUS = 'Agenda status'
    EVT_DETAIL_TEXT_MINUTES = 'Published minutes'
    EVT_DETAIL_TEXT_MINUTES_STATUS = 'Minutes status'
    EVT_DETAIL_TEXT_SUMMARY = 'Published summary'

    EVT_DETAIL_DATETIME_FORMAT = EVT_TABLE_DATETIME_FORMAT

    EVT_DETAIL_PUPA_KEY_NAME = EVT_DETAIL_TEXT_TOPIC
    EVT_DETAIL_PUPA_KEY_LOCATION = EVT_DETAIL_TEXT_LOCATION

    EVT_DETAIL_PUPA_PARTICIPANTS = {
        'organization': [EVT_DETAIL_TEXT_NAME]
        }

    EVT_DETAIL_PUPA_DOCUMENTS = [
        EVT_DETAIL_TEXT_AGENDA,
        EVT_DETAIL_TEXT_MINUTES,
        EVT_DETAIL_TEXT_NOTICE,
        EVT_DETAIL_TEXT_VIDEO,
        ]

    # ------------------------------------------------------------------------
    # Bill search config.
    BILLS_SIMPLE_SEARCH_TEXT = '<<< Simple Search'
    BILLS_ADVANCED_SEARCH_TEXT = 'Detailed Search >>>'

    # Requests args.
    proxies = dict.fromkeys(['http', 'https'], 'http://localhost:8080')
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.6) '
            'Gecko/20070725 Firefox/2.0.0.6')
        }
    requests_kwargs = dict(
        proxies=proxies,
        headers=headers)

    @CachedAttr
    def client(self):
        '''The requests.Session-like object used to make web requests;
        usually a scrapelib.Scraper.
        '''
        client = Client(self)
        self.ctx['client'] = client
        return client

    @CachedAttr
    def ctx(self):
        '''An inheritable/overriddable dict for this config's helper
        views to access. Make it initially point back to this config object.
        '''
        ctx = ChainMap()
        ctx.update(config=self, url=self.root_url)
        return ctx
