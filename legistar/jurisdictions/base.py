import os
import json
import logging
import logging.config
import importlib.machinery
from urllib.parse import urlparse
from collections import ChainMap, defaultdict
from os.path import dirname, abspath, join

import pytz
import requests
from opencivicdata import common as ocd_common

import legistar
from legistar.client import Client
from legistar.base import Base, CachedAttr, NoClobberDict
from legistar.jurisdictions.utils import Tabs, Mediatypes, Views
from legistar.jurisdictions.utils import overrides, try_jxn_delegation
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

        # Add (div_id, classn) for strict use with pupa.
        classification = attrs.get('classification')
        if classification is not None:
            JXN_CONFIGS[(division_id, classification)] = cls

        # Also nicknames.
        for name in attrs.get('nicknames', []):
            JXN_CONFIGS[name] = cls

        meta.collect_itemfuncs(attrs, cls)
        meta.collect_overrides(attrs, cls)

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
        cls.aggregator_funcs = dict(registry)

    @classmethod
    def collect_overrides(meta, attrs, cls):
        '''Aggregates overrides for later reference by the
        try_jxn_delegation decorator.
        '''
        registry = defaultdict(NoClobberDict)
        for name, member in attrs.items():
            if getattr(member, '_is_override', False):
                clsname = member._override_clsname
                membname = member._override_membername
                registry[clsname][membname] = member
        cls.override_funcs = dict(registry)


class ConfigError(Exception):
    '''For complaining about config issues.
    '''


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

    FASTMODE = False
    SESSION_CLASS = requests.Session

    # UTC timezone for creating fully tz qualified datetimes.
    _utc = pytz.timezone('UTC')

    @CachedAttr
    def timezone(self):
        '''Returns pytz.timezone instance for the jxn's TIMEZONE setting.
        '''
        try:
            tz = self.TIMEZONE
        except AttributeError as e:
            msg = 'Please set TIMEZONE on %r' % self
            raise ConfigError(msg) from e
        return pytz.timezone(tz)

    def datetime_add_tz(self, dt):
        '''Add fully qualified timezone to dt.
        '''
        return self.timezone.localize(dt).astimezone(self._utc)

    mediatypes = Mediatypes()
    MEDIATYPE_GIF_PDF = ('/images/pdf.gif', 'application/pdf')
    MEDIATYPE_EXT_PDF = ('pdf', 'application/pdf')
    MEDIATYPE_GIF_VIDEO = ('/images/video.gif', 'application/x-shockwave-flash')
    MEDIATYPE_EXT_DOC = ('doc', 'application/vnd.msword')
    MEDIATYPE_EXT_DOCX = ('docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')

    TAB_TEXT_ID = 'ctl00_tabTop'
    TAB_TEXT_XPATH_TMPL = 'string(//div[@id="%s"]//a[contains(@class, "rtsSelected")])'
    TAB_TEXT_XPATH = TAB_TEXT_XPATH_TMPL % TAB_TEXT_ID

    # These are config options that can be overridden.
    tabs = Tabs()
    EVT_TAB_META = ('Calendar.aspx', 'events')
    ORG_TAB_META = ('Departments.aspx', 'orgs')
    BILL_TAB_META = ('Legislation.aspx', 'bills')
    PPL_TAB_META = ('People.aspx', 'people')

    # Pagination xpaths.
    PGN_CURRENT_PAGE_TMPL = '//*[contains(@class, "%s")]'
    PGN_CURRENT_PAGE_CLASS = 'rgCurrentPage'
    PGN_CURRENT_PAGE_XPATH = PGN_CURRENT_PAGE_TMPL % PGN_CURRENT_PAGE_CLASS
    PGN_NEXT_PAGE_TMPL = '%s/following-sibling::a[1]'
    PGN_NEXT_PAGE_XPATH = 'string(%s/following-sibling::a[1]/@href)' % PGN_CURRENT_PAGE_XPATH

    views = Views()

    NO_RECORDS_FOUND_TEXT = ['No records were found', 'No records to display.']
    # This text is shown if something is wrong with the query.
    # Bad request, basically. Means the code needs edits.
    BAD_QUERY_TEXT = ['Please enter your search criteria.']
    RESULTS_TABLE_XPATH = '//table[contains(@class, "rgMaster")]'

    # ------------------------------------------------------------------------
    # Orgs general config.
    # ------------------------------------------------------------------------
    # Which pupatype legistar scraper should be used to generate the list of
    # orgs at the beginning of a pupa scrape.
    GET_ORGS_FROM = 'orgs'
    EXCLUDE_TOPLEVEL_ORG_MEMBERSHIPS = True

    ORG_SEARCH_VIEW_CLASS = 'legistar.orgs.OrgsSearchView'
    ORG_DETAIL_VIEW_CLASS = 'legistar.orgs.OrgsDetailView'
    ORG_SEARCH_TABLE_CLASS = 'legistar.orgs.OrgsSearchTable'
    ORG_SEARCH_TABLEROW_CLASS = 'legistar.orgs.OrgsSearchTableRow'
    ORG_SEARCH_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    ORG_SEARCH_FORM_CLASS = 'legistar.orgs.OrgsSearchForm'
    ORG_DETAIL_TABLE_CLASS = 'legistar.orgs.OrgsDetailTable'
    ORG_DETAIL_TABLEROW_CLASS = 'legistar.orgs.OrgsDetailTableRow'
    ORG_DETAIL_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    ORG_DETAIL_FORM_CLASS = 'legistar.orgs.OrgsDetailForm'

    # Scrapers will be getting this from people pages.
    ORG_SEARCH_TABLE_DETAIL_AVAILABLE = False
    ORG_DETAIL_TABLE_DETAIL_AVAILABLE = False

    ORG_SEARCH_TABLE_TEXT_NAME = 'Department Name'
    ORG_SEARCH_TABLE_TEXT_TYPE = 'Type'
    ORG_SEARCH_TABLE_TEXT_MEETING_LOCATION = 'Meeting Location'
    ORG_SEARCH_TABLE_TEXT_NUM_VACANCIES = 'Vacancies'
    ORG_SEARCH_TABLE_TEXT_NUM_MEMBERS = 'Members'

    ORG_DEFAULT_CLASSIFICATIONS = ChainMap({
        'Department': 'commission',
        'Clerk': 'commission',
        'Executive Office': 'commission',
        'Primary Legislative Body': 'legislature',
        'Legislative Body': 'legislature',
        'Secondary Legislative Body': 'legislature',
        'City Council': 'legislature',
        'Board of Supervisors': 'legislature',
        'Agency': 'commission',
        'Task Force': 'commission',
        })

    @property
    def _ORG_CLASSIFICATIONS(self):
        '''Make the Config's clasifications inherit from this default set.
        '''
        classn = getattr(self, 'ORG_CLASSIFICATIONS', {})
        return self.ORG_DEFAULT_CLASSIFICATIONS.new_child(classn)

    def get_org_classification(self, orgtype):
        '''Convert the legistar org table `type` column into
        a pupa classification.
        '''
        # Try to get the classn from the subtype.
        classn = self._ORG_CLASSIFICATIONS.get(orgtype)
        if classn is not None:
            return classn

        # Bah, no matches--try to guess it.
        type_lower = orgtype.lower()
        for classn in ('legislature', 'party', 'committee', 'commission'):
            if classn in type_lower:
                return classn

        other = [('board', 'commission')]
        for word, classn in other:
            if word in type_lower:
                return classn

        # Not found--complain.
        msg = '''
            Couldn't convert organization `type` value %r to a pupa
            organization classification (see http://opencivicdata.readthedocs.org/en/latest/data/organization.html#basics).
            Please edit %r by adding a top-level ORG_CLASSIFICATIONS
            dictionary that maps %r value to a pupa classification.'''
        raise ConfigError(msg % (orgtype, self.config, orgtype))

    # ------------------------------------------------------------------------
    # Events general config.
    # ------------------------------------------------------------------------
    EVT_SEARCH_VIEW_CLASS = 'legistar.events.EventsSearchView'
    EVT_DETAIL_VIEW_CLASS = 'legistar.events.EventsDetailView'
    EVT_SEARCH_TABLE_CLASS = 'legistar.events.EventsSearchTable'
    EVT_SEARCH_TABLEROW_CLASS = 'legistar.events.EventsSearchTableRow'
    EVT_SEARCH_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    EVT_SEARCH_FORM_CLASS = 'legistar.events.EventsSearchForm'
    EVT_DETAIL_TABLE_CLASS = 'legistar.events.EventsDetailTable'
    EVT_DETAIL_TABLEROW_CLASS = 'legistar.events.EventsDetailTableRow'
    EVT_DETAIL_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    EVT_DETAIL_FORM_CLASS = 'legistar.events.EventsDetailForm'

    # ------------------------------------------------------------------------
    # Events search table config.

    # Search params.
    EVT_SEARCH_TIME_PERIOD = 'This Month'
    EVT_SEARCH_BODIES = 'All Committees'
    EVT_SEARCH_BODIES_EL_NAME = 'ctl00$ContentPlaceHolder1$lstBodies'
    EVT_SEARCH_TIME_PERIOD_EL_NAME = 'ctl00$ContentPlaceHolder1$lstYears'
    EVT_SEARCH_CLIENTSTATE_EL_NAME = 'ctl00_ContentPlaceHolder1_lstYears_ClientState'

    # Table
    EVT_SEARCH_TABLE_TEXT_NAME = 'Name'
    EVT_SEARCH_TABLE_TEXT_DATE =  'Meeting Date'
    EVT_SEARCH_TABLE_TEXT_ICAL =  ''
    EVT_SEARCH_TABLE_TEXT_TIME = 'Meeting Time'
    EVT_SEARCH_TABLE_TEXT_LOCATION = 'Meeting Location'
    EVT_SEARCH_TABLE_TEXT_TOPIC = 'Meeting Topic'
    EVT_SEARCH_TABLE_TEXT_DETAILS = 'Meeting Details'
    EVT_SEARCH_TABLE_TEXT_AGENDA = 'Agenda'
    EVT_SEARCH_TABLE_TEXT_MINUTES = 'Minutes'
    EVT_SEARCH_TABLE_TEXT_VIDEO = 'Video'
    EVT_SEARCH_TABLE_TEXT_AUDIO = 'Audio'  # sfgov has this
    EVT_SEARCH_TABLE_TEXT_NOTICE = 'Notice'
    EVT_SEARCH_TABLE_TEXT_TRANSCRIPT = 'Transcript'

    EVT_SEARCH_TABLE_DATETIME_FORMAT = '%m/%d/%Y %I:%M %p'

    EVT_SEARCH_TABLE_PUPA_KEY_NAME = EVT_SEARCH_TABLE_TEXT_TOPIC
    EVT_SEARCH_TABLE_PUPA_KEY_LOCATION = EVT_SEARCH_TABLE_TEXT_LOCATION

    EVT_SEARCH_TABLE_PUPA_PARTICIPANTS = {
        'organization': [EVT_SEARCH_TABLE_TEXT_NAME]
        }

    EVT_SEARCH_TABLE_PUPA_DOCUMENTS = [
        EVT_SEARCH_TABLE_TEXT_AGENDA,
        EVT_SEARCH_TABLE_TEXT_MINUTES,
        EVT_SEARCH_TABLE_TEXT_NOTICE,
        ]

    EVT_SEARCH_TABLE_PUPA_MEDIA = [
        EVT_SEARCH_TABLE_TEXT_VIDEO,
        EVT_SEARCH_TABLE_TEXT_AUDIO,
        ]

    # ------------------------------------------------------------------------
    # Events detail config.
    EVT_SEARCH_TABLE_DETAIL_AVAILABLE = True
    EVT_DETAIL_TABLE_DETAIL_AVAILABLE = False

    EVT_DETAIL_TEXT_NAME = EVT_SEARCH_TABLE_TEXT_NAME
    EVT_DETAIL_TEXT_TOPIC = EVT_SEARCH_TABLE_TEXT_TOPIC
    EVT_DETAIL_TEXT_DETAILS = EVT_SEARCH_TABLE_TEXT_DETAILS
    EVT_DETAIL_TEXT_VIDEO = EVT_SEARCH_TABLE_TEXT_VIDEO
    EVT_DETAIL_TEXT_AUDIO = EVT_SEARCH_TABLE_TEXT_AUDIO
    EVT_DETAIL_TEXT_NOTICE = EVT_SEARCH_TABLE_TEXT_NOTICE
    EVT_DETAIL_TEXT_LOCATION = 'Meeting location'
    EVT_DETAIL_TEXT_DATE = 'Date'
    EVT_DETAIL_TEXT_TIME = 'Time'
    EVT_DETAIL_TEXT_AGENDA = 'Published agenda'
    EVT_DETAIL_TEXT_AGENDA_STATUS = 'Agenda status'
    EVT_DETAIL_TEXT_MINUTES = 'Published minutes'
    EVT_DETAIL_TEXT_MINUTES_STATUS = 'Minutes status'
    EVT_DETAIL_TEXT_SUMMARY = 'Published summary'

    EVT_DETAIL_DATETIME_FORMAT = EVT_SEARCH_TABLE_DATETIME_FORMAT
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

    EVT_DETAIL_PUPA_MEDIA = [
        EVT_DETAIL_TEXT_VIDEO,
        EVT_DETAIL_TEXT_AUDIO,
        ]

    # Readable text for the agenda table of related bills.
    EVT_DETAIL_TABLE_TEXT_FILE_NUMBER = 'File #'
    EVT_DETAIL_TABLE_TEXT_VERSION = 'Ver.'
    EVT_DETAIL_TABLE_TEXT_NAME = 'Name'
    EVT_DETAIL_TABLE_TEXT_AGENDA_NOTE = 'Agenda Note'
    EVT_DETAIL_TABLE_TEXT_AGENDA_NUMBER = 'Agenda #'
    EVT_DETAIL_TABLE_TEXT_TYPE = 'Type'
    EVT_DETAIL_TABLE_TEXT_TITLE = 'Title'
    EVT_DETAIL_TABLE_TEXT_ACTION = 'Action'
    EVT_DETAIL_TABLE_TEXT_RESULT = 'Result'
    EVT_DETAIL_TABLE_TEXT_ACTION_DETAILS = 'Action Details'
    EVT_DETAIL_TABLE_TEXT_VIDEO = 'Video'
    EVT_DETAIL_TABLE_TEXT_AUDIO = 'Audio'
    EVT_DETAIL_TABLE_TEXT_TRANSCRIPT = 'Transcript'

    EVT_DETAIL_TABLE_PUPA_MEDIA = [
        EVT_DETAIL_TABLE_TEXT_VIDEO,
        EVT_DETAIL_TABLE_TEXT_AUDIO,
        ]

    # ------------------------------------------------------------------------
    # People
    # ------------------------------------------------------------------------
    PPL_PARTY_REQUIRED = True

    # View class config.
    PPL_SEARCH_VIEW_CLASS = 'legistar.people.PeopleSearchView'
    PPL_DETAIL_VIEW_CLASS = 'legistar.people.PeopleDetailView'
    PPL_SEARCH_TABLE_CLASS = 'legistar.people.PeopleSearchTable'
    PPL_SEARCH_TABLEROW_CLASS = 'legistar.people.PeopleSearchTableRow'
    PPL_SEARCH_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    PPL_SEARCH_FORM_CLASS = 'legistar.people.PeopleSearchForm'
    PPL_DETAIL_TABLE_CLASS = 'legistar.people.PeopleDetailTable'
    PPL_DETAIL_TABLEROW_CLASS = 'legistar.people.PeopleDetailTableRow'
    PPL_DETAIL_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    PPL_DETAIL_FORM_CLASS = 'legistar.people.PeopleDetailForm'

    # People search config.
    PPL_SEARCH_TABLE_TEXT_FULLNAME = 'Person Name'
    PPL_SEARCH_TABLE_TEXT_WEBSITE =  'Web Site'
    PPL_SEARCH_TABLE_TEXT_EMAIL =  'E-mail'
    PPL_SEARCH_TABLE_TEXT_FAX = 'Fax'
    PPL_SEARCH_TABLE_TEXT_DISTRICT = 'Ward/Office'
    PPL_SEARCH_TABLE_TEXT_DISTRICT_PHONE = 'Ward Office Phone'
    PPL_SEARCH_TABLE_TEXT_DISTRICT_ADDRESS = 'Ward Office Address'
    PPL_SEARCH_TABLE_TEXT_DISTRICT_ADDRESS_STATE = ('State', 0)
    PPL_SEARCH_TABLE_TEXT_DISTRICT_ADDRESS_CITY = ('City', 0)
    PPL_SEARCH_TABLE_TEXT_DISTRICT_ADDRESS_ZIP = ('Zip', 0)
    PPL_SEARCH_TABLE_TEXT_CITYHALL_PHONE = 'City Hall Phone'
    PPL_SEARCH_TABLE_TEXT_CITYHALL_ADDRESS = 'City Hall Address'
    PPL_SEARCH_TABLE_TEXT_CITYHALL_ADDRESS_STATE = ('State', 1)
    PPL_SEARCH_TABLE_TEXT_CITYHALL_ADDRESS_CITY = ('City', 1)
    PPL_SEARCH_TABLE_TEXT_CITYHALL_ADDRESS_ZIP = ('Zip', 1)

    # Whether people detail pages are available.
    PPL_SEARCH_TABLE_DETAIL_AVAILABLE = True
    # Nonsense to prevent detail queries on detail pages.
    PPL_DETAIL_TABLE_DETAIL_AVAILABLE = False

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
    TOPLEVEL_ORG_MEMBERSHIP_TITLE = 'Council Member'
    TOPLEVEL_ORG_MEMBERSHIP_NAME = 'City Council'

    PPL_DETAIL_TABLE_TEXT_ORG = 'Department Name'
    PPL_DETAIL_TABLE_TEXT_ROLE = 'Title'
    PPL_DETAIL_TABLE_TEXT_START_DATE = 'Start Date'
    PPL_DETAIL_TABLE_TEXT_END_DATE = 'End Date'
    PPL_DETAIL_TABLE_TEXT_APPOINTED_BY = 'Appointed By'

    # ------------------------------------------------------------------------
    # Bill search classes.
    # ------------------------------------------------------------------------
    BILL_SEARCH_VIEW_CLASS = 'legistar.bills.BillsSearchView'
    BILL_DETAIL_VIEW_CLASS = 'legistar.bills.BillsDetailView'
    BILL_SEARCH_TABLE_CLASS = 'legistar.bills.BillsSearchTable'
    BILL_SEARCH_TABLEROW_CLASS = 'legistar.bills.BillsSearchTableRow'
    BILL_SEARCH_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    BILL_SEARCH_FORM_CLASS = 'legistar.bills.BillsSearchForm'
    BILL_DETAIL_TABLE_CLASS = 'legistar.bills.BillsDetailTable'
    BILL_DETAIL_TABLEROW_CLASS = 'legistar.bills.BillsDetailTableRow'
    BILL_DETAIL_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'
    BILL_DETAIL_FORM_CLASS = 'legistar.bills.BillsDetailForm'
    BILL_ACTION_VIEW_CLASS = 'legistar.bills.BillsDetailAction'
    BILL_ACTION_TABLE_CLASS = 'legistar.bills.BillsDetailActionTable'
    BILL_ACTION_TABLEROW_CLASS = 'legistar.bills.BillsDetailActionTableRow'
    BILL_ACTION_TABLECELL_CLASS = 'legistar.fields.ElementAccessor'

    # ------------------------------------------------------------------------
    # Bill search config.
    # ------------------------------------------------------------------------
    # The element name of the link to switch btw simple, advanced search.
    BILL_SEARCH_SWITCH_EL_ID = 'ctl00_ContentPlaceHolder1_btnSwitch'
    # The button text to switch to simple search, normalized to lower case.
    BILL_SEARCH_SWITCH_SIMPLE = 'simple search'

    # Simple search form.
    BILL_SEARCH_TIME_PERIOD = 'This Year'
    BILL_SEARCH_TYPES = 'All Types'
    BILL_SEARCH_TYPES_EL_NAME = 'ctl00$ContentPlaceHolder1$lstTypeBasic'
    BILL_SEARCH_TIME_PERIOD_EL_NAME = 'ctl00$ContentPlaceHolder1$lstYears'
    BILL_SEARCH_CLIENTSTATE_EL_NAME = 'ctl00_ContentPlaceHolder1_lstYears_ClientState'
    BILL_SEARCH_ID = BILL_SEARCH_TEXT = 'on'
    BILL_SEARCH_ID_EL_NAME = 'ctl00$ContentPlaceHolder1$chkID'
    BILL_SEARCH_TEXT_EL_NAME = 'ctl00$ContentPlaceHolder1$chkText'
    BILL_SEARCH_BUTTON_EL_NAME = 'ctl00$ContentPlaceHolder1$btnSearch'
    BILL_SEARCH_BUTTON = 'Search Legislation'

    # Variants for the advanced search form.
    BILL_SEARCH_ADVANCED_TYPES_EL_NAME = 'ctl00$ContentPlaceHolder1$lstType'
    BILL_SEARCH_ADVANCED_TIME_PERIOD_EL_NAME = 'ctl00$ContentPlaceHolder1$lstYearsAdvanced'
    BILL_SEARCH_ADVANCED_BUTTON_EL_NAME = 'ctl00$ContentPlaceHolder1$btnSearch2'
    BILL_SEARCH_ADVANCED_BUTTON = BILL_SEARCH_BUTTON

    # Search table.
    BILL_SEARCH_TABLE_TEXT_FILE_NUMBER = 'File #'
    BILL_SEARCH_TABLE_TEXT_LAW_NUMBER = 'Law Number'
    BILL_SEARCH_TABLE_TEXT_TYPE = 'Type'
    BILL_SEARCH_TABLE_TEXT_STATUS = 'Status'
    BILL_SEARCH_TABLE_TEXT_INTRO_DATE = 'Intro Date'
    BILL_SEARCH_TABLE_TEXT_FILE_CREATED = 'File Created'
    BILL_SEARCH_TABLE_TEXT_FINAL_ACTION = 'Final Action'
    BILL_SEARCH_TABLE_TEXT_TITLE = 'Title'

    # Weird/random ones.
    BILL_SEARCH_TABLE_TEXT_SPONSOR_OFFICE = "Main Sponsor's Ward/Office"

    BILL_SEARCH_TABLE_DATETIME_FORMAT = '%m/%d/%Y'
    # BILL_SEARCH_TABLE_PUPA_KEY_NAME = BILL_SEARCH_TABLE_TEXT_TOPIC
    # BILL_SEARCH_TABLE_PUPA_KEY_LOCATION = BILL_SEARCH_TABLE_TEXT_LOCATION

    # ------------------------------------------------------------------------
    # Bill detail config.
    BILL_SEARCH_TABLE_DETAIL_AVAILABLE = True
    BILL_DETAIL_TABLE_DETAIL_AVAILABLE = True
    BILL_ACTION_DETAIL_AVAILABLE = False

    BILL_DETAIL_TEXT_FILE_NUMBER = 'File2'
    BILL_DETAIL_TEXT_VERSION = 'Version'
    BILL_DETAIL_TEXT_TYPE = 'Type2'
    BILL_DETAIL_TEXT_LAW_NUMBER = BILL_SEARCH_TABLE_TEXT_LAW_NUMBER
    BILL_DETAIL_TEXT_FINAL_ACTION = 'Final action'
    BILL_DETAIL_TEXT_NAME = 'Name'
    BILL_DETAIL_TEXT_STATUS = BILL_SEARCH_TABLE_TEXT_STATUS
    BILL_DETAIL_TEXT_CREATED = 'Introduced2'
    BILL_DETAIL_TEXT_AGENDA = 'OnAgenda2'
    BILL_DETAIL_TEXT_ENACTMENT_DATE = 'Enactment date'
    BILL_DETAIL_TEXT_TITLE = 'Title2'
    BILL_DETAIL_TEXT_SPONSORS = 'Sponsors2'
    BILL_DETAIL_TEXT_ATTACHMENTS = 'Attachments2'
    BILL_DETAIL_TEXT_COMMITTEE = 'Committee'

    BILL_DETAIL_DATETIME_FORMAT = BILL_SEARCH_TABLE_DATETIME_FORMAT
    # BILL_DETAIL_PUPA_KEY_NAME = BILL_DETAIL_TEXT_TOPIC
    # BILL_DETAIL_PUPA_KEY_LOCATION = BILL_DETAIL_TEXT_LOCATION

    # Bill detail table rows.
    BILL_DETAIL_TABLE_TEXT_DATE = 'Date'
    BILL_DETAIL_TABLE_TEXT_VERSION = 'Ver.'
    BILL_DETAIL_TABLE_TEXT_ACTION_BY = 'Action By'
    BILL_DETAIL_TABLE_TEXT_ACTION = 'Action'
    BILL_DETAIL_TABLE_TEXT_RESULT = 'Result'
    BILL_DETAIL_TABLE_TEXT_ACTION_DETAILS = 'Action Details'
    BILL_DETAIL_TEXT_FINAL_ACTION = 'Final action'
    BILL_DETAIL_TABLE_TEXT_MEETING_DETAILS = 'Meeting Details'
    BILL_DETAIL_TABLE_TEXT_MUTLIMEDIA = 'Multimedia'
    BILL_DETAIL_TABLE_TEXT_TRANSCRIPT = 'Transcript'
    BILL_DETAIL_TABLE_TEXT_AUDIO = 'Audio'
    BILL_DETAIL_TABLE_TEXT_VIDEO = 'Video'

    # Weird ones--Chicago.
    BILL_DETAIL_TABLE_TEXT_JOURNAL_PAGE = 'Journal Page Number'

    BILL_DETAIL_TABLE_DATETIME_FORMAT = BILL_DETAIL_DATETIME_FORMAT
    BILL_DETAIL_TABLE_PUPA_MEDIA = [
        BILL_DETAIL_TABLE_TEXT_MUTLIMEDIA,
        BILL_DETAIL_TABLE_TEXT_TRANSCRIPT,
        BILL_DETAIL_TABLE_TEXT_AUDIO,
        BILL_DETAIL_TABLE_TEXT_VIDEO,
        ]

    BILL_ACTION_TEXT_FILE_NUMBER = 'File #'
    BILL_ACTION_TEXT_TYPE = 'Type'
    BILL_ACTION_TEXT_VERSION = 'Version'
    BILL_ACTION_TEXT_TITLE = 'Title'
    BILL_ACTION_TEXT_MOVER = 'Mover'
    BILL_ACTION_TEXT_SECONDER = 'Seconder'
    BILL_ACTION_TEXT_RESULT = 'Result'
    BILL_ACTION_TEXT_AGENDA_NOTE = 'Agenda note'
    BILL_ACTION_TEXT_MINUTES_NOTE = 'Minutes note'
    BILL_ACTION_TEXT_ACTION = 'Action'
    BILL_ACTION_TEXT_ACTION_TEXT = 'Action text'
    BILL_ACTION_TEXT_PERSON = 'Person Name'
    BILL_ACTION_TEXT_VOTE = 'Vote'

    BILL_DEFAULT_VOTE_OPTION_MAP =  ChainMap({
        'yes': 'yes',
        'aye': 'yes',
        'yea': 'yes',
        'affirmative': 'yes',
        'no': 'no',
        'nay': 'no',
        'negative': 'no',
        'absent': 'absent',
        'non voting': 'not voting',
        'not voting': 'not voting',
        'excused': 'excused',
        'abstain': 'abstain',
        'conflict': 'abstain',
        'maternity': 'excused',
        'recused': 'excused',
        })

    @property
    def _BILL_VOTE_OPTION_MAP(self):
        options = getattr(self, 'BILL_VOTE_OPTION_MAP', {})
        return self.BILL_DEFAULT_VOTE_OPTION_MAP.new_child(options)

    BILL_DEFAULT_VOTE_RESULT_MAP =  ChainMap({
        'pass': 'pass',
        'passed': 'pass',
        'fail': 'fail',
        'failed': 'fail',
        })

    @property
    def _BILL_VOTE_RESULT_MAP(self):
        options = getattr(self, 'BILL_VOTE_RESULT_MAP', {})
        return self.BILL_DEFAULT_VOTE_RESULT_MAP.new_child(options)

    BILL_DEFAULT_CLASSIFICATIONS = ChainMap({
        })

    @property
    def _BILL_CLASSIFICATIONS(self):
        '''Make the Config's clasifications inherit from this default set.
        '''
        classn = getattr(self, 'BILL_CLASSIFICATIONS', {})
        return self.BILL_DEFAULT_CLASSIFICATIONS.new_child(classn)

    # ------------------------------------------------------------------------
    # Requests client config.
    # ------------------------------------------------------------------------

    # Client sleeping is disabled by default, because the main use of this
    # library is with http://github.com/opencivicdata/pupa, which delegates
    # requests-per-minute, retries, and backoffs with
    # http://github.com/sunlightlabs/scrapelib
    DO_CLIENT_SLEEP = True
    SLEEP_RANGE = (5, 20)

    REQUEST_HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.6) '
            'Gecko/20070725 Firefox/2.0.0.6')
        }

    # Route the requests through mitmproxy. http://mitmproxy.org/
    # ENABLE_PROXIES = True
    ENABLE_PROXIES = False
    proxies = dict.fromkeys(['http', 'https'], 'http://localhost:8080')
    requests_kwargs = dict(
        headers=REQUEST_HEADERS)

    if ENABLE_PROXIES:
        requests_kwargs['proxies'] = proxies

    @classmethod
    def get_host(cls):
        '''Returns just the host from the url.
        '''
        return urlparse(cls.root_url).netloc

    def get_session(self):
        '''Return a requests.Session subtype, or something that provides
        the same interface.
        '''
        session = self.kwargs.get('session')
        if session is None:
            session = self.SESSION_CLASS()
            if self.FASTMODE:
                session.cache_write_only = False
        return session

    def get_client(self):
        '''The requests.Session-like object used to make web requests;
        usually a scrapelib.Scraper.
        '''
        client = self.chainmap['client'] = self.make_child(Client)
        return client

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
            info=logger.info,
            error=logger.error,
            debug=logger.debug,
            warning=logger.warning,
            critical=logger.critical,
            exception=logger.exception)
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
            # 'requests': {
            #     'handlers': ['default'], 'level': 'DEBUG', 'propagate': False
            # },
        },
    }

    # -----------------------------------------------------------------------
    # Jxn-level org caching, for pupa.
    # -----------------------------------------------------------------------
    @CachedAttr
    def org_cache(self):
        return {}

    # -----------------------------------------------------------------------
    # Stuff related to testing.
    # -----------------------------------------------------------------------
    def get_assertions_dir(self, year):
        '''Return the fully qualified path to this jxn's folder
        containing output uni assertions (see http://github.com/twneale/uni).
        '''
        legistar_root = abspath(join(dirname(legistar.__file__), '..'))
        assertions = join(legistar_root, 'assertions')
        _, relpath = self.division_id.split('/', 1)
        fullpath = join(assertions, relpath, year)
        return fullpath

    def ensure_assertions_dir(self, year):
        '''Verify the asserts dir exists, otherwise create and return it.
        '''
        assertions_dir = self.get_assertions_dir(year)
        if not os.path.isdir(assertions_dir):
            os.makedirs(assertions_dir)
        return assertions_dir

    def gen_assertions(self, year, pupatype):
        '''Yield each assertions contained in the asserts module for
        `year` and `pupatype`.
        '''
        assertions_dir = self.ensure_assertions_dir(year)
        filename = join(assertions_dir, '%s.py' % pupatype)
        loader = importlib.machinery.SourceFileLoader(pupatype, filename)
        mod = loader.load_module()
        if not hasattr(mod, 'assertions'):
            msg = ('The file %r must define a module-level sequence '
                   '`assertions` containing the assertion data.')
            raise Exception(msg % filename)
        yield from iter(mod.assertions)