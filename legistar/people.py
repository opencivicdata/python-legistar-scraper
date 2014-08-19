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
        'Ward Office Phone': 'district_phone',
        'Ward Office Address': 'district_address',
        'City Hall Phone': 'city_hall_phone',
        'City Hall Address': 'city_hall_phone',
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
        'Ward Office Phone': 'district_phone',
        'Ward Office Fax': 'district_fax',
        'Ward Office Address': 'district_address',
        'City Hall Phone': 'city_hall_phone',
        'City Hall Fax': 'city_hall_fax',
        'City Hall Address': 'city_hall_phone',
        'City, state zip': None,
        'City, State Zip': None,
        '': None,
    }

    def obj_from_dict(self, item):
        district = item.pop('district', None)
        if district:
            district = district.lstrip('0')

        p = Person(name=item.pop('name'),
                   district=district,
                   primary_org=item.pop('primary_org', self.DEFAULT_PRIMARY_ORG),
                   party=item.pop('party', None),
                   image=item.pop('image', ''),
                  )
        for ctype in ('email', 'phone', 'address', 'fax'):
            value = item.pop(ctype, None)
            if value:
                p.add_contact_detail(type=ctype, value=value)

        if item.get('url'):
           p.add_link(item.pop('url'))

        if 'last_name' in item:
            p.sort_name = item.pop('last_name')

        for source in item.pop('sources'):
            p.add_source(source)

        for field in self.EXTRA_FIELDS:
            val = item.pop(field)
            if val:
                p.extras[field] = val

        assert not item, list(item.keys())

        return p

    # unused
    CREATE_LEGISLATURE_MEMBERSHIP = False
    PPL_PARTY_REQUIRED = True

    PPL_DETAIL_TEXT_PHOTO = 'Photo'

    PPL_DETAIL_TABLE_TEXT_ORG = 'Department Name'
    PPL_DETAIL_TABLE_TEXT_ROLE = 'Title'
    PPL_DETAIL_TABLE_TEXT_START_DATE = 'Start Date'
    PPL_DETAIL_TABLE_TEXT_END_DATE = 'End Date'
    PPL_DETAIL_TABLE_TEXT_APPOINTED_BY = 'Appointed By'
