from urllib.parse import urlparse

from legistar import settings
from legistar.jxn_config import Config
from legistar.rootview import get_scraper
# from legistar.jurisdictions.nyc import Config as NycConfig
import legistar.jurisdictions


if __name__ == '__main__':
    import pprint
    url = 'http://legistar.council.nyc.gov/'
    scraper = get_scraper(url)
    for data in scraper.gen_events():
        pprint.pprint(data)
        import pdb; pdb.set_trace()
