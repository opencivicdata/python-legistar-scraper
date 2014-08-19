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

        for key, val in list(item.items()):
            for ctype in ('email', 'voice', 'address', 'fax'):
                if key.startswith(ctype):
                    item.pop(key)
                    if val:
                        pieces = key.split('-', 1)
                        ctype = pieces[0]
                        note = pieces[1] if len(pieces) == 2 else ''
                        p.add_contact_detail(type=ctype, value=val, note=note)

        url = item.pop('url')
        if url:
           p.add_link(url)

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
