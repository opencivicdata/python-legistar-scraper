from legistar.jurisdictions.base import Config


class NYC(Config):
    nicknames = ['nyc']
    root_url = 'http://legistar.council.nyc.gov/'


class Chicago(Config):
    nicknames = ['windy']
    root_url = 'https://chicago.legistar.com'


class SanFrancisco(Config):
    nicknames = ['sf', 'frisco']
    root_url = 'https://sfgov.legistar.com'


class Philadelphia(Config):
    nicknames = ['philly', 'pa']
    root_url = 'https://phila.legistar.com/'
    EVT_DETAIL_AVAILABLE = False


class JonesBoro(Config):
    nicknames = ['jojo']
    root_url = 'http://jonesboro.legistar.com/'


class Solano(Config):
    nicknames = ['solano']
    root_url = 'https://solano.legistar.com'

