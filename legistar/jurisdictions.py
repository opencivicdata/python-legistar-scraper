from legistar.jxn_config import Config


class NYC(Config):
    root_url = 'http://legistar.council.nyc.gov/'


class Chicago(Config):
    root_url = 'https://chicago.legistar.com'
    EVENTS_TAB_META = ('Calendar.aspx', 'Meetings', 'events')


class SanFrancisco(Config):
    root_url = 'https://sfgov.legistar.com'
    PEOPLE_TAB_META = ('MainBody.aspx', 'Board of Supervisors', 'people')

