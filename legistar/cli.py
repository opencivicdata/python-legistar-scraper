import sys
import pprint
import argparse

from legistar import get_scraper


def run():
    # url = 'http://legistar.council.nyc.gov/'
    # url = 'https://chicago.legistar.com'
    # url = 'https://sfgov.legistar.com'
    parser = argparse.ArgumentParser(description='Scrape a Legistar CMS instance.')
    parser.add_argument('pupatype', help="bills, people, events, committees")
    parser.add_argument('jurisdiction', help=(
        "A jurisdiction's nickname, ocd_id, or url, defined in its config, "
        "found in the module legistar.jurisdictions.config"))
    args = parser.parse_args()

    key = args.jurisdiction
    if key.startswith('http'):
        scraper = get_scraper(url=key)
    else:
        scraper = get_scraper(key)
    for data in scraper.gen_pupatype_objects(args.pupatype):
        pprint.pprint(data)
        import pdb; pdb.set_trace()
