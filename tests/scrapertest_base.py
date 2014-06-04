from abc import abstractproperty

from uni import MatchSet
from legistar import get_scraper
from tests.utils import get_fixture, gen_assertions


class ScrapertestBase:

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
        pass

    def setup(self):
        self.count = 0
        self.scraper = get_scraper(self.DIVISION_ID)
        self.config = self.scraper.config

    def test_output(self):
        view = self.scraper.get_pupatype_searchview(self.PUPATYPE)
        assertions = self.config.gen_assertions(str(self.YEAR), self.PUPATYPE)
        with MatchSet(assertions) as checker:
            for data in view:
                checker.check(data)
                self.count += 1
                if self.MAX_RECORDS < self.count:
                    break
        assert checker.success
