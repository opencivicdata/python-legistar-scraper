from uni import AssertionSet

from tests.scrapertest_base import ScrapertestBase


class TestNewYorkPeople2014(ScrapertestBase):
    DIVISION_ID = 'ocd-division/country:us/state:ny/place:new_york'
    PUPATYPE = 'people'
    YEAR = 2014
    MAX_RECORDS = 10


class TestNewYorkOrgs2014(ScrapertestBase):
    DIVISION_ID = 'ocd-division/country:us/state:ny/place:new_york'
    PUPATYPE = 'orgs'
    YEAR = 2014
    MAX_RECORDS = 10


class TestNewYorkEvents2014(ScrapertestBase):
    DIVISION_ID = 'ocd-division/country:us/state:ny/place:new_york'
    PUPATYPE = 'events'
    YEAR = 2014
    MAX_RECORDS = 10
    CHECKER = AssertionSet


class TestNewYorkBills2014(ScrapertestBase):
    DIVISION_ID = 'ocd-division/country:us/state:ny/place:new_york'
    PUPATYPE = 'bills'
    YEAR = 2014
    MAX_RECORDS = 3
    CHECKER = AssertionSet
