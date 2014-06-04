from tests.scrapertest_base import ScrapertestBase


class TestChicagoPeople2014(ScrapertestBase):
    DIVISION_ID = 'ocd-jurisdiction/country:us/state:il/place:chicago'
    PUPATYPE = 'people'
    YEAR = 2014
    MAX_RECORDS = 10


class TestChicagoOrgs2014(ScrapertestBase):
    DIVISION_ID = 'ocd-jurisdiction/country:us/state:il/place:chicago'
    PUPATYPE = 'orgs'
    YEAR = 2014
    MAX_RECORDS = 10

