import os
import json

import lxml


def fixture_path(*segs):
    FIXTURES = ('tests', 'fixtures')
    path = os.path.join(*FIXTURES + segs)
    return path


def get_fixture(*segs):
    path = fixture_path(*segs)
    with open(path) as f:
        doc = lxml.html.fromstring(f.read())
    return doc


def gen_assertions(*segs):
    path = fixture_path(*segs)
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            yield json.loads(line)
