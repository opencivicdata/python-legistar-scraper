import os
import sys

import lxml

from src.legistar.ui.bills import LegistarBillScraper
from src.legistar.ui.events import LegistarEventsScraper
from src.legistar.ui.people import LegistarPersonScraper


def save_page(page, jurisdiction, outfile):
    test_directory = os.path.abspath(os.path.dirname(__file__))
    project_directory = os.path.join(test_directory, '..')

    with open(os.path.join(project_directory, 'tests', 'fixtures', jurisdiction, outfile), 'wb') as f:
        f.write(lxml.html.tostring(page))


def refresh_bills(jurisdiction):
    s = LegistarBillScraper()
    s.LEGISLATION_URL = 'https://{}.legistar.com/Legislation.aspx'.format(jurisdiction)

    page = next(s.search_legislation('bus'))

    save_page(page, jurisdiction, 'bills.html')


def refresh_events(jurisdiction):
    s = LegistarEventsScraper()
    s.EVENTSPAGE = 'https://{}.legistar.com/Calendar.aspx'.format(jurisdiction)

    page = next(s.event_pages('2018-01-01'))

    save_page(page, jurisdiction, 'events.html')


def refresh_people(jurisdiction):
    s = LegistarPersonScraper()
    MEMBERLIST = 'https://{}.legistar.com/People.aspx'.format(jurisdiction)

    page = next(s.pages(MEMBERLIST))

    save_page(page, jurisdiction, 'people.html')


if __name__ == '__main__':
    try:
        _, jurisdictions = sys.argv
        jurisdictions = jurisdictions.split(',')
    except ValueError:
        jurisdictions = ('chicago', 'metro', 'nyc')

    for j in jurisdictions:
        refresh_bills(j)
        refresh_events(j)
        refresh_people(j)
