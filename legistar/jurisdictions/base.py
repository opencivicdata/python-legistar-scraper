import logging
import logging.config
from urllib.parse import urlparse
from collections import namedtuple, ChainMap

import requests
from hercules import CachedAttr

from legistar.client import Client
from legistar.base.chainmap import CtxMixin


PUPATYPES = ('events', 'orgs', 'people', 'bills')
PUPATYPE_PREFIXES = [s.upper() for s in PUPATYPES]

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': "%(asctime)s %(levelname)s %(name)s: %(message)s",
            'datefmt': '%H:%M:%S'
        }
    },
    'handlers': {
        'default': {'level': 'DEBUG',
                    'class': 'legistar.utils.ansistrm.ColorizingStreamHandler',
                    'formatter': 'standard'},
    },
    'loggers': {
        'legistar': {
            'handlers': ['default'], 'level': 'DEBUG', 'propagate': False
        },
        'requests': {
            'handlers': ['default'], 'level': 'DEBUG', 'propagate': False
        },
    },
}
logging.config.dictConfig(LOGGING_CONFIG)


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
    '''Desceriptor to help in aggregating TAB* metadata on jxn config types.
    '''
    TabItemMeta = namedtuple('TabMeta', 'path, text, pupatype')

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

    def get_by_text(self, tabtext):
        for tab in self._gen_tabs():
            if tabtext == tab.text:
                return tab


class MimetypeGifMeta:
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
    '''Metaclass that aggregates jurisdiction config types by root_url
    and ocd_id.
    '''
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
    '''The base configuration for a Legistar instance. Various parts can be
    overridden.
    '''
    def __init__(self, **kwargs):
        '''Thinking it'd be helpful to store get_scraper kwargs here,
        in case the Config subtype is the most convenient place to put
        a helper function.
        '''
        self.kwargs = kwargs

    SESSION_CLASS = requests.Session

    gif_mimetypes = MimetypeGifMeta()
    # Preceding slashes are necessary
    MIMETYPE_GIF_PDF = ('/images/pdf.gif', 'application/pdf')
    MIMETYPE_EXT_PDF = ('pdf', 'application/pdf')
    MIMETYPE_GIF_VIDEO = ('/images/video.gif', 'application/x-shockwave-flash')
    MIMETYPE_EXT_DOC = ('doc', 'application/vnd.msword')
    MIMETYPE_EXT_DOCX = ('docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')

    TAB_TEXT_ID = 'ctl00_tabTop'
    TAB_TEXT_XPATH_TMPL = 'string(//div[@id="%s"]//a[contains(@class, "rtsSelected")])'
    TAB_TEXT_XPATH = TAB_TEXT_XPATH_TMPL % TAB_TEXT_ID

    # These are config options that can be overridden.
    tabs = TabMeta()
    EVENTS_TAB_META = ('Calendar.aspx', 'Calendar', 'events')
    ORGS_TAB_META = ('Departments.aspx', 'Committees', 'orgs')
    BILLS_TAB_META = ('Legislation.aspx', 'Legislation', 'bills')
    PEOPLE_TAB_META = ('MainBody.aspx', 'City Council', 'people')

    # Pagination xpaths.
    PGN_CURRENT_PAGE_TMPL = '//*[contains(@class, "%s")]'
    PGN_CURRENT_PAGE_CLASS = 'rgCurrentPage'
    PGN_CURRENT_PAGE_XPATH = PGN_CURRENT_PAGE_TMPL % PGN_CURRENT_PAGE_CLASS
    PGN_NEXT_PAGE_TMPL = '%s/following-sibling::a[1]'
    PGN_NEXT_PAGE_XPATH = 'string(%s/following-sibling::a[1]/@href)' % PGN_CURRENT_PAGE_XPATH

    viewmeta = ViewsMeta()
    EVENTS_SEARCH_VIEW_CLASS = 'legistar.events.SearchView'
    EVENTS_DETAIL_VIEW_CLASS = 'legistar.events.DetailView'
    EVENTS_SEARCH_TABLE_CLASS = 'legistar.events.SearchTable'
    EVENTS_SEARCH_TABLEROW_CLASS = 'legistar.events.SearchTableRow'
    EVENTS_SEARCH_TABLECELL_CLASS = 'legistar.fields.ElementWrapper'
    EVENTS_SEARCH_FORM_CLASS = 'legistar.events.SearchForm'
    EVENTS_DETAIL_TABLE_CLASS = 'legistar.events.DetailTable'
    EVENTS_DETAIL_TABLEROW_CLASS = 'legistar.events.DetailTableRow'
    EVENTS_DETAIL_TABLECELL_CLASS = 'legistar.fields.ElementWrapper'
    EVENTS_DETAIL_FORM_CLASS = 'legistar.events.DetailForm'

    # ORGS_SEARCH_VIEW_CLASS = 'legistar.orgs.SearchView'
    # ORGS_DETAIL_VIEW_CLASS = 'legistar.orgs.DetailView'
    # ORGS_SEARCH_TABLE_CLASS = 'legistar.orgs.SearchTable'
    # ORGS_SEARCH_TABLEROW_CLASS = 'legistar.orgs.search.table.TableRow'
    # ORGS_SEARCH_TABLECELL_CLASS = 'legistar.fields.ElementWrapper'
    # ORGS_SEARCH_FORM_CLASS = 'legistar.orgs.search.form.Form'
    # ORGS_DETAIL_TABLE_CLASS = 'legistar.orgs.detail.table.Table'
    # ORGS_DETAIL_TABLEROW_CLASS = 'legistar.orgs.detail.table.TableRow'
    # ORGS_DETAIL_TABLECELL_CLASS = 'legistar.fields.ElementWrapper'
    # ORGS_DETAIL_FORM_CLASS = 'legistar.orgs.detail.form.Form'

    # PEOPLE_SEARCH_VIEW_CLASS = 'legistar.people.SearchView'
    # PEOPLE_DETAIL_VIEW_CLASS = 'legistar.people.DetailView'
    # PEOPLE_SEARCH_TABLE_CLASS = 'legistar.people.search.table.Table'
    # PEOPLE_SEARCH_TABLEROW_CLASS = 'legistar.people.search.table.TableRow'
    # PEOPLE_SEARCH_TABLECELL_CLASS = 'legistar.fields.ElementWrapper'
    # PEOPLE_SEARCH_FORM_CLASS = 'legistar.people.search.form.Form'
    # PEOPLE_DETAIL_TABLE_CLASS = 'legistar.people.detail.table.Table'
    # PEOPLE_DETAIL_TABLEROW_CLASS = 'legistar.people.detail.table.TableRow'
    # PEOPLE_DETAIL_TABLECELL_CLASS = 'legistar.fields.ElementWrapper'
    # PEOPLE_DETAIL_FORM_CLASS = 'legistar.people.detail.form.Form'

    # BILLS_SEARCH_VIEW_CLASS = 'legistar.bills.SearchView'
    # BILLS_DETAIL_VIEW_CLASS = 'legistar.bills.DetailView'
    # BILLS_SEARCH_TABLE_CLASS = 'legistar.bills.search.table.Table'
    # BILLS_SEARCH_TABLEROW_CLASS = 'legistar.bills.search.table.TableRow'
    # BILLS_SEARCH_TABLECELL_CLASS = 'legistar.fields.ElementWrapper'
    # BILLS_SEARCH_FORM_CLASS = 'legistar.bills.search.form.Form'
    # BILLS_DETAIL_TABLE_CLASS = 'legistar.bills.detail.table.Table'
    # BILLS_DETAIL_TABLEROW_CLASS = 'legistar.bills.detail.table.TableRow'
    # BILLS_DETAIL_TABLECELL_CLASS = 'legistar.fields.ElementWrapper'
    # BILLS_DETAIL_FORM_CLASS = 'legistar.bills.detail.form.Form'

    NO_RECORDS_FOUND_TEXT = ['No records were found', 'No records to display.']
    RESULTS_TABLE_XPATH = '//table[contains(@class, "rgMaster")]'

    # ------------------------------------------------------------------------
    # Events general config.
    # ------------------------------------------------------------------------
    EVENTS_SEARCH_TIME_PERIOD = 'This Year'
    EVENTS_SEARCH_BODIES = 'All Committees'
    EVENTS_SEARCH_BODIES_EL_NAME = 'ctl00$ContentPlaceHolder1$lstBodies'
    EVENTS_SEARCH_TIME_PERIOD_EL_NAME = 'ctl00$ContentPlaceHolder1$lstYears'
    EVENTS_SEARCH_CLIENTSTATE_EL_NAME = 'ctl00_ContentPlaceHolder1_lstYears_ClientState'

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

    # REadable text for the agenda table of related bills.
    EVT_AGENDA_TABLE_TEXT_FILE_NUMBER = 'File #'
    EVT_AGENDA_TABLE_TEXT_VERSION = 'Ver.'
    EVT_AGENDA_TABLE_TEXT_NAME = 'Name'
    EVT_AGENDA_TABLE_TEXT_AGENDA_NOTE = 'Agenda Note'
    EVT_AGENDA_TABLE_TEXT_AGENDA_NUMBER = 'Agenda #'
    EVT_AGENDA_TABLE_TEXT_TYPE = 'Type'
    EVT_AGENDA_TABLE_TEXT_TITLE = 'Title'
    EVT_AGENDA_TABLE_TEXT_ACTION = 'Action'
    EVT_AGENDA_TABLE_TEXT_RESULT = 'Result'
    EVT_AGENDA_TABLE_TEXT_ACTION_DETAILS = 'Action Details'
    EVT_AGENDA_TABLE_TEXT_VIDEO = 'Video'
    EVT_AGENDA_TABLE_TEXT_AUDIO = 'Audio'
    EVT_AGENDA_TABLE_TEXT_TRANSCRIPT = 'Transcript'

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
    requests_kwargs = {}

    def get_client(self):
        '''The requests.Session-like object used to make web requests;
        usually a scrapelib.Scraper.
        '''
        return Client(self)

    def get_logger(self):
        '''Get a configured logger.
        '''
        logger = logging.getLogger('legistar')
        if 'loglevel' in self.kwargs:
            logger.setLevel(self.kwargs['loglevel'])
        return logger

    @CachedAttr
    def chainmap(self):
        '''An inheritable/overridable dict for this config's helper
        views to access. Make it initially point back to this config object.

        Other objects that inherit this chainmap can access self.info, etc.
        '''
        logger = self.get_logger()
        chainmap = ChainMap()
        chainmap.update(
            config=self,
            url=self.root_url,
            client=self.get_client(),
            info=logger.info,
            error=logger.error,
            debug=logger.debug,
            warning=logger.warning,
            critical=logger.critical)
        return chainmap
