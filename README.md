Python Legistar Scraper
=======================

[![Build Status](https://travis-ci.org/opencivicdata/python-legistar-scraper.svg?branch=master)](https://travis-ci.org/opencivicdata/python-legistar-scraper)

Scrapes municipal data from Legistar sites.

## Contributing

### Local installation

Install this package and its dependencies. (We recommend working in a virtual
environment, e.g., [`venv`](https://docs.python.org/3/library/venv.html) or
[`virtualenvwrapper`](https://virtualenvwrapper.readthedocs.io/en/latest/)).

```bash
pip install -e .
```

Install the development requirements.

```bash
pip install -r requirements.txt
```

### Testing

To run the tests:

```bash
pytest -sv
```

#### A note on test fixtures

The tests rely on HTML from assorted Legistar properties. As it would be
undesirable to hit the live server each time the tests are run, particularly
during local development, fixtures are provided in the `tests/fixtures/`
directory.

A convenience script is provided for refreshing the fixtures, i.e., re-scraping
Legistar and storing the resultant HTML.

The Legistar site is fairly stable, however if your patch addresses a change
in page structure, update the fixtures as follows:

```bash
python tests/refresh_fixtures.py
```

Be sure to commit the refreshed fixture and submit it with your patch.
