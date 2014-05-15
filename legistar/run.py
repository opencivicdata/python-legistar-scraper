from legistar import get_scraper


if __name__ == '__main__':
    import sys
    import pprint

    # url = 'http://legistar.council.nyc.gov/'
    # url = 'https://chicago.legistar.com'
    # url = 'https://sfgov.legistar.com'
    url = sys.argv[1]
    scraper = get_scraper(url)
    for data in scraper.gen_events():
        pprint.pprint(data)
        import pdb; pdb.set_trace()
