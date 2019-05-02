import re

import requests_mock


def test_topics(api_bill_scraper, matter_index, all_indexes):
    with requests_mock.Mocker() as m:
        matter_matcher = re.compile(r'/indexes')
        m.get(matter_matcher, json=matter_index, status_code=200)

        all_matcher = re.compile(r'/matterindexes')
        m.get(all_matcher, json=all_indexes, status_code=200)

        matter_topics = api_bill_scraper.topics('some_id')
        all_topics = list(api_bill_scraper.topics())

        # Assert only matter indexes are returned when matter ID passed
        assert len(matter_index) == len(matter_topics)

        # Assert all indexes returned when no matter ID passed
        assert len(all_indexes) == len(all_topics)
