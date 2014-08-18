import urllib

import pytz

class Config:
    """ a config class by which all the variable parts of the scrapers can be implemented """

    ## unprocessed ##

    _utc = pytz.timezone('UTC')

    def datetime_add_tz(self, dt):
        '''Add fully qualified timezone to dt. '''
        return pytz.timezone(self.TIMEZONE).localize(dt).astimezone(self._utc)

    MEDIATYPE_GIF_PDF = ('/images/pdf.gif', 'application/pdf')
    MEDIATYPE_GIF_VIDEO = ('/images/video.gif', 'application/x-shockwave-flash')
    MEDIATYPE_EXT_PDF = ('pdf', 'application/pdf')
    MEDIATYPE_EXT_DOC = ('doc', 'application/vnd.msword')
    MEDIATYPE_EXT_DOCX = ('docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')


    # Pagination xpaths.
    PGN_CURRENT_PAGE_TMPL = '//*[contains(@class, "%s")]'
    PGN_CURRENT_PAGE_CLASS = 'rgCurrentPage'
    PGN_CURRENT_PAGE_XPATH = PGN_CURRENT_PAGE_TMPL % PGN_CURRENT_PAGE_CLASS
    PGN_NEXT_PAGE_TMPL = '%s/following-sibling::a[1]'
    PGN_NEXT_PAGE_XPATH = 'string(%s/following-sibling::a[1]/@href)' % PGN_CURRENT_PAGE_XPATH


    # ------------------------------------------------------------------------
    # Orgs general config.
    # ------------------------------------------------------------------------
    # Which pupatype legistar scraper should be used to generate the list of
    # orgs at the beginning of a pupa scrape.
    EXCLUDE_TOPLEVEL_ORG_MEMBERSHIPS = True

    # Scrapers will be getting this from people pages.
    ORG_SEARCH_TABLE_DETAIL_AVAILABLE = False
    ORG_DETAIL_TABLE_DETAIL_AVAILABLE = False

    ORG_SEARCH_TABLE_TEXT_NAME = 'Department Name'
    ORG_SEARCH_TABLE_TEXT_TYPE = 'Type'
    ORG_SEARCH_TABLE_TEXT_MEETING_LOCATION = 'Meeting Location'
    ORG_SEARCH_TABLE_TEXT_NUM_VACANCIES = 'Vacancies'
    ORG_SEARCH_TABLE_TEXT_NUM_MEMBERS = 'Members'

    ORG_DEFAULT_CLASSIFICATIONS = {
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
    }

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
    EVT_SEARCH_SUBMIT_BUTTON_NAME = 'ctl00$ContentPlaceHolder1$btnSearch'

    # ------------------------------------------------------------------------
    # Events search table config.

    # Search params.
    EVT_SEARCH_TIME_PERIOD = 'This Year'
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
    CREATE_LEGISLATURE_MEMBERSHIP = False
    PPL_PARTY_REQUIRED = True

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
    # Bill search config.
    # ------------------------------------------------------------------------
    # The element name of the link to switch btw simple, advanced search.
    BILL_SEARCH_SUBMIT_BUTTON_NAME = 'ctl00$ContentPlaceHolder1$btnSearch2'
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

    BILL_DEFAULT_VOTE_OPTION_MAP =  {
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
    }

    @property
    def _BILL_VOTE_OPTION_MAP(self):
        options = getattr(self, 'BILL_VOTE_OPTION_MAP', {})
        return self.BILL_DEFAULT_VOTE_OPTION_MAP.new_child(options)

    BILL_DEFAULT_VOTE_RESULT_MAP =  {
        'pass': 'pass',
        'passed': 'pass',
        'fail': 'fail',
        'failed': 'fail',
        }

    @property
    def _BILL_VOTE_RESULT_MAP(self):
        options = getattr(self, 'BILL_VOTE_RESULT_MAP', {})
        return self.BILL_DEFAULT_VOTE_RESULT_MAP.new_child(options)

    BILL_DEFAULT_CLASSIFICATIONS = { }

    @property
    def _BILL_CLASSIFICATIONS(self):
        '''Make the Config's clasifications inherit from this default set.
        '''
        classn = getattr(self, 'BILL_CLASSIFICATIONS', {})
        return self.BILL_DEFAULT_CLASSIFICATIONS.new_child(classn)

    # ------------------------------------------------------------------------
    # Requests client config.
    # ------------------------------------------------------------------------

    REQUEST_HEADERS = {
        'User-Agent': ('Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.6) '
                       'Gecko/20070725 Firefox/2.0.0.6')
    }
    requests_kwargs = dict(headers=REQUEST_HEADERS)
