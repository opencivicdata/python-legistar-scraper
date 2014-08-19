from pupa.scrape import Person
from .base import LegistarScraper


class LegistarPersonScraper(LegistarScraper):

    #TABS = {'events': 'Calendar.aspx', 'orgs': 'Departments.aspx', 'bills': 'Legislation.aspx',}
    SEARCH_PAGE = 'People.aspx'
    DEFAULT_PRIMARY_ORG = None
    SEARCH_ROW_MAPPING = {
        'Person Name': 'name',
        'Name': 'name',
        'Web Site': 'url',
        'Ward/Office': 'district',
        'E-mail': 'email',
        'Website': 'url',
        'Ward Office Phone': 'voice-district',
        'Ward Office Address': 'address-district',
        'City Hall Phone': 'voice-city hall',
        'City Hall Address': 'address-city hall',
        'Fax': 'fax',
        'City': None,
        'State': None,
        'Zip': None,
    }
    DETAIL_PAGE_MAPPING = {
        'First name': None,
        'Last name': 'last_name',
        'E-mail': 'email',
        'Web site': 'url',
        'Website': 'url',
        'Notes': 'notes',
        'Ward Office Phone': 'voice-district',
        'Ward Office Fax': 'fax-district',
        'Ward Office Address': 'address-district',
        'City Hall Phone': 'voice-city hall',
        'City Hall Fax': 'fax-city hall',
        'City Hall Address': 'address-city hall',
        'City, state zip': None,
        'City, State Zip': None,
        '': None,
    }
    REQUIRED_FIELDS = ('name',)
    OPTIONAL_FIELDS = ('birth_date', 'death_date', 'biography', 'summary', 'image',
                       'gender', 'national_identity', 'start_date', 'end_date', 'party')
    PUPA_TYPE = Person

    def _modify_object_args(self, kwargs, item):
        # district & primary org are special cases
        district = item.pop('district', None)
        if district:
            kwargs['district'] = district.lstrip('0')
        kwargs['primary_org'] = item.pop('primary_org', self.DEFAULT_PRIMARY_ORG)

    def _modify_created_object(self, obj, item):
        # TODO: does this actually work?
        if 'last_name' in item:
            obj.sort_name = item.pop('last_name')

    # unused
    PPL_DETAIL_TABLE_TEXT_ORG = 'Department Name'
    PPL_DETAIL_TABLE_TEXT_ROLE = 'Title'
    PPL_DETAIL_TABLE_TEXT_START_DATE = 'Start Date'
    PPL_DETAIL_TABLE_TEXT_END_DATE = 'End Date'
    PPL_DETAIL_TABLE_TEXT_APPOINTED_BY = 'Appointed By'
