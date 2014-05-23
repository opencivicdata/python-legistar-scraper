import json


def get_fixture(self, domain, filename):
    FIXTURES = ('tests', 'fixtures')
    FIXTURES += (domain, filename)
    path = os.path.join(*FIXTURES)
    doc = lxml.html.parse(path)
    return doc.getroot()


def gen_assertions(self, domain, filename):
    FIXTURES = ('tests', 'fixtures')
    FIXTURES += (domain, filename)
    path = os.path.join(*FIXTURES)
    with open(path) as f:
        for line in f:
            yield json.loads(line)
