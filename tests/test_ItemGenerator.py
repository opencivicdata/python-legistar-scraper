from legistar.utils.itemgenerator import ItemGenerator, make_item


class CowItems(ItemGenerator):

    @make_item('cow', wrapwith=int)
    def getcow(self):
        return '3'

    @make_item('moos', wrapwith=tuple)
    def getmoos(self):
        yield 'moo'
        yield 'moo0'
        yield 'mooooo'

    @make_item('size')
    def getsize(self):
        return 'huge'

    @make_item('heffer')
    def failmoo(self):
        raise self.SkipItem()


class TestItemGenerator:

    def test_output(self):
        expected = {
            'cow': 3,
            'size': 'huge',
            'moos': ('moo', 'moo0', 'mooooo'),
            }
        assert dict(CowItems()) == expected