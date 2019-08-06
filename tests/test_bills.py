import re

import requests_mock


def test_topics(metro_api_bill_scraper, matter_index, all_indexes):
    with requests_mock.Mocker() as m:
        matter_matcher = re.compile(r'/matters/5036/indexes')
        m.get(matter_matcher, json=matter_index, status_code=200)

        all_matcher = re.compile(r'/metro/indexes')
        m.get(all_matcher, json=all_indexes, status_code=200)

        matter_topics = metro_api_bill_scraper.topics(5036)
        all_topics = list(metro_api_bill_scraper.topics())

        # Assert only matter indexes are returned when matter ID passed
        assert len(matter_index) == len(matter_topics)

        # Assert all indexes returned when no matter ID passed
        assert len(all_indexes) == len(all_topics)


def test_duplicate_events(chicago_api_bill_scraper, caplog, dupe_event):
    with requests_mock.Mocker() as m:
        event_matcher = re.compile('/matters/38768/histories')
        m.get(event_matcher, json=dupe_event, status_code=200)

        chicago_api_bill_scraper.history('38768')
        assert 'appears more than once' in caplog.text


def test_no_duplicate(chicago_api_bill_scraper, caplog, no_dupe_event):
    with requests_mock.Mocker() as m:
        event_matcher = re.compile('/matters/38769/histories')
        m.get(event_matcher, json=no_dupe_event, status_code=200)

        chicago_api_bill_scraper.history('38769')
        assert 'appears more than once' not in caplog.text


def test_404_votes(chicago_api_bill_scraper):
    with requests_mock.Mocker() as m:
        m.get(re.compile(r'.*'), status_code=404)
        votes = chicago_api_bill_scraper.votes('408134')
        assert votes == []
