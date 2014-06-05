from abc import abstractproperty

from uni import MatchSet
from legistar import get_scraper


class ScrapertestBase:
    '''This base class knows how to retrieve assertions data for
    the given DIVISION_ID, PUPATYPE and YEAR.
    '''
    @abstractproperty
    def DIVISION_ID(self):
        pass

    @abstractproperty
    def PUPATYPE(self):
        pass

    @abstractproperty
    def YEAR(self):
        pass

    @abstractproperty
    def MAX_RECORDS(self):
        '''The max number of records to return before stopping.
        '''
        pass

    @property
    def CHECKER(self):
        return MatchSet

    def setup(self):
        self.count = 0
        self.scraper = get_scraper(self.DIVISION_ID)
        self.config = self.scraper.config

    def test_output(self):
        view = self.scraper.get_pupatype_searchview(self.PUPATYPE)
        assertions = self.config.gen_assertions(str(self.YEAR), self.PUPATYPE)
        with self.CHECKER(assertions) as checker:
            for data in view:
                checker.check(data)
                self.count += 1
                if self.MAX_RECORDS < self.count:
                    break
        assert checker.success
