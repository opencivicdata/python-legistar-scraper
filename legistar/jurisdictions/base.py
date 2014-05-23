import logging
import logging.config
from urllib.parse import urlparse
from collections import ChainMap, defaultdict

import requests

from legistar.client import Client
from legistar.base import Base, CachedAttr
from legistar.jurisdictions.utils import Tabs, Mimetypes, Views
from legistar.utils.itemgenerator import make_item

JXN_CONFIGS = {}


class ConfigMeta(type):
    '''Metaclass that aggregates jurisdiction config types by root_url
    and division_id.
    '''
    def __new__(meta, name, bases, attrs):
        cls = type.__new__(meta, name, bases, attrs)

        # Track by domain.
        root_url = attrs.get('root_url')
        if root_url is not None:
            JXN_CONFIGS[cls.get_host()] = cls

        # Also OCD id.
        division_id = attrs.get('division_id')
        if division_id is not None:
            JXN_CONFIGS[division_id] = cls

        # Also nicknames.
        for name in attrs.get('nicknames', []):
            JXN_CONFIGS[name] = cls

        meta.collect_itemfuncs(attrs, cls)

        return cls

    @classmethod
    def collect_itemfuncs(meta, attrs, cls):
        '''Aggregates special item functions marked on each
        config subtype.
        '''
        registry = defaultdict(list)
        for name, member in attrs.items():
            if getattr(member, '_is_aggregator_func', False):
                registry[member._pupatype].append(member)
        cls.aggregator_funcs = registry


class Config(Base, metaclass=ConfigMeta):
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

    mimetypes = Mimetypes()
    MIMETYPE_GIF_PDF = ('/images/pdf.gif', 'application/pdf')
    MIMETYPE_EXT_PDF = ('pdf', 'application/pdf')
    MIMETYPE_GIF_VIDEO = ('/images/video.gif', 'application/x-shockwave-flash')
    MIMETYPE_EXT_DOC = ('doc', 'application/vnd.msword')
    MIMETYPE_EXT_DOCX = ('docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')

    TAB_TEXT_ID = 'ctl00_tabTop'
    TAB_TEXT_XPATH_TMPL = 'string(//div[@id="%s"]//a[contains(@class, "rtsSelected")])'
    TAB_TEXT_XPATH = TAB_TEXT_XPATH_TMPL % TAB_TEXT_ID

    # These are config options that can be overridden.
    tabs = Tabs()
    EVENTS_TAB_META = ('Calendar.aspx', 'events')
    ORGS_TAB_META = ('Departments.aspx', 'orgs')
    BILLS_TAB_META = ('Legislation.aspx', 'bills')
    PEOPLE_TAB_META = ('People.aspx', 'people')

    # Pagination xpaths.
    PGN_CURRENT_PAGE_TMPL = '//*[contains(@class, "%s")]'
    PGN_CURRENT_PAGE_CLASS = 'rgCurrentPage'
    PGN_CURRENT_PAGE_XPATH = PGN_CURRENT_PAGE_TMPL % PGN_CURRENT_PAGE_CLASS
    PGN_NEXT_PAGE_TMPL = '%s/following-sibling::a[1]'
    PGN_NEXT_PAGE_XPATH = 'string(%s/following-sibling::a[1]/@href)' % PGN_CURRENT_PAGE_XPATH

    views = Views()
    EVENTS_SEARCH_VIEW_CLASS = 'legistar.events.SearchView'
    EVENTS_DETAIL_VIEW_CLASS = 'legistar.events.DetailView'
    EVENTS_SEARCH_TABLE_CLASS = 'legistar.events.SearchTable'
    EVENTS_SEARCH_TABLEROW_CLASS = 'legistar.events.SearchTableRow'
    EVENTS_SEARCH_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    EVENTS_SEARCH_FORM_CLASS = 'legistar.events.SearchForm'
    EVENTS_DETAIL_TABLE_CLASS = 'legistar.events.DetailTable'
    EVENTS_DETAIL_TABLEROW_CLASS = 'legistar.events.DetailTableRow'
    EVENTS_DETAIL_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    EVENTS_DETAIL_FORM_CLASS = 'legistar.events.DetailForm'

    ORGS_SEARCH_VIEW_CLASS = 'legistar.orgs.SearchView'
    ORGS_DETAIL_VIEW_CLASS = 'legistar.orgs.DetailView'
    ORGS_SEARCH_TABLE_CLASS = 'legistar.orgs.SearchTable'
    ORGS_SEARCH_TABLEROW_CLASS = 'legistar.orgs.SearchTableRow'
    ORGS_SEARCH_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    ORGS_SEARCH_FORM_CLASS = 'legistar.orgs.SearchForm'
    ORGS_DETAIL_TABLE_CLASS = 'legistar.orgs.DetailTable'
    ORGS_DETAIL_TABLEROW_CLASS = 'legistar.orgs.DetailTableRow'
    ORGS_DETAIL_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    ORGS_DETAIL_FORM_CLASS = 'legistar.orgs.DetailForm'

    PEOPLE_SEARCH_VIEW_CLASS = 'legistar.people.SearchView'
    PEOPLE_DETAIL_VIEW_CLASS = 'legistar.people.DetailView'
    PEOPLE_SEARCH_TABLE_CLASS = 'legistar.people.SearchTable'
    PEOPLE_SEARCH_TABLEROW_CLASS = 'legistar.people.SearchTableRow'
    PEOPLE_SEARCH_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    PEOPLE_SEARCH_FORM_CLASS = 'legistar.people.SearchForm'
    PEOPLE_DETAIL_TABLE_CLASS = 'legistar.people.DetailTable'
    PEOPLE_DETAIL_TABLEROW_CLASS = 'legistar.people.DetailTableRow'
    PEOPLE_DETAIL_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    PEOPLE_DETAIL_FORM_CLASS = 'legistar.people.DetailForm'

    BILLS_SEARCH_VIEW_CLASS = 'legistar.bills.SearchView'
    BILLS_DETAIL_VIEW_CLASS = 'legistar.bills.DetailView'
    BILLS_SEARCH_TABLE_CLASS = 'legistar.bills.SearchTable'
    BILLS_SEARCH_TABLEROW_CLASS = 'legistar.bills.SearchTableRow'
    BILLS_SEARCH_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    BILLS_SEARCH_FORM_CLASS = 'legistar.bills.SearchForm'
    BILLS_DETAIL_TABLE_CLASS = 'legistar.bills.DetailTable'
    BILLS_DETAIL_TABLEROW_CLASS = 'legistar.bills.DetailTableRow'
    BILLS_DETAIL_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    BILLS_DETAIL_FORM_CLASS = 'legistar.bills.DetailForm'

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
    EVT_DETAIL_AVAILABLE = True

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
    # People search config.
    PPL_TABLE_TEXT_FULLNAME = 'Person Name'
    PPL_TABLE_TEXT_WEBSITE =  'Web Site'
    PPL_TABLE_TEXT_EMAIL =  'E-mail'
    PPL_TABLE_TEXT_DISTRICT_FAX = 'Fax'
    PPL_TABLE_TEXT_DISTRICT = 'Ward/Office'
    PPL_TABLE_TEXT_DISTRICT_PHONE = 'Ward Office Phone'
    PPL_TABLE_TEXT_DISTRICT_ADDRESS = 'Ward Office Address'
    PPL_TABLE_TEXT_DISTRICT_ADDRESS_CITY = 'Ward Office Address'

    PPL_DETAIL_TEXT_FIRSTNAME = 'First name'
    PPL_DETAIL_TEXT_LASTNAME = 'Last name'
    PPL_DETAIL_TEXT_WEBSITE =  'Web site'
    PPL_DETAIL_TEXT_EMAIL = 'E-mail'
    PPL_DETAIL_TEXT_NOTES = 'Notes'

    # This field actually has no label, but this pretends it does,
    # so as to support the same interface.
    PPL_DETAIL_TEXT_PHOTO = 'Photo'

    # The string to indicate that person's rep'n is "at-large".
    DEFAULT_AT_LARGE_STRING = 'At-Large'
    # The string indicating person's membership in the council, for example.
    # This is usually the first row in the person detail chamber.
    # It's the string value of the first PPL_MEMB_TABLE_TEXT_ROLE
    TOPLEVEL_ORG_MEMBERSHIP_TITLE_TEXT = 'Council Member'
    TOPLEVEL_ORG_MEMBERSHIP_NAME_TEXT = 'City Council'

    PPL_MEMB_TABLE_TEXT_ORG = 'Department Name'
    PPL_MEMB_TABLE_TEXT_ROLE = 'Title'
    PPL_MEMB_TABLE_TEXT_START_DATE = 'Start Date'
    PPL_MEMB_TABLE_TEXT_END_DATE = 'End Date'
    PPL_MEMB_TABLE_TEXT_APPOINTED_BY = 'Appointed By'

    # ------------------------------------------------------------------------
    # Bill search config.
    BILLS_SIMPLE_SEARCH_TEXT = '<<< Simple Search'
    BILLS_ADVANCED_SEARCH_TEXT = 'Detailed Search >>>'

    # ------------------------------------------------------------------------
    # Settings to prevent web requests during testing.

    # Makes the form use the default table data without posting a query.
    USING_TEST_CONFIG = False

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

    @classmethod
    def get_host(cls):
        return urlparse(cls.root_url).netloc

    def get_session(self):
        '''Return a requests.Session subtype, or something that provides
        the same interface.
        '''
        session = self.kwargs.get('session')
        if session is None:
            session = self.SESSION_CLASS()
        return session

    def get_client(self):
        '''The requests.Session-like object used to make web requests;
        usually a scrapelib.Scraper.
        '''
        return Client(self)

    def get_logger(self):
        '''Get a configured logger.
        '''
        logging.config.dictConfig(self.LOGGING_CONFIG)
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
