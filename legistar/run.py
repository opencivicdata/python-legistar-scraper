from legistar import get_scraper


if __name__ == '__main__':
    import sys
    import pprint

    # url = 'http://legistar.council.nyc.gov/'
    # url = 'https://chicago.legistar.com'
    # url = 'https://sfgov.legistar.com'
    key = sys.argv[1]
    if key.startswith('http'):
        scraper = get_scraper(url=key)
    else:
        scraper = get_scraper(key=key)
    for data in scraper.gen_events():
        pprint.pprint(data)
        import pdb; pdb.set_trace()
