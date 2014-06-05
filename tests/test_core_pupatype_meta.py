'''Tests for legistar/pupatypes.py
'''
import pytest

from legistar.base import Base
from legistar.pupatypes import PupatypeMixin
from legistar.jurisdictions.config import NYC
from legistar.pupatypes import TypePrefix, VALID_PUPATYPES


class PeopleSearchTable(Base, PupatypeMixin):
    pass

config = NYC()


class TestPupatypePeople:

    obj = config.make_child(PeopleSearchTable)

    def test_get_label_text(self):
        text = self.obj.get_label_text('website')
        assert text == self.obj.config.PPL_SEARCH_TABLE_TEXT_WEBSITE

        text = self.obj.get_label_text('fullname')
        assert text == self.obj.config.PPL_SEARCH_TABLE_TEXT_FULLNAME

        text = self.obj.get_label_text('email')
        assert text == self.obj.config.PPL_SEARCH_TABLE_TEXT_EMAIL

        text = self.obj.get_label_text('district_phone')
        assert text == self.obj.config.PPL_SEARCH_TABLE_TEXT_DISTRICT_PHONE

        text = self.obj.get_label_text('district_address')
        assert text == self.obj.config.PPL_SEARCH_TABLE_TEXT_DISTRICT_ADDRESS


class EventsDetailTable(Base, PupatypeMixin):
    pass


class TestPupatypeEvents:

    obj = config.make_child(EventsDetailTable)

    def test_get_label_text(self):
        text = self.obj.get_label_text('action')
        assert text == self.obj.config.EVT_DETAIL_TABLE_TEXT_ACTION

        text = self.obj.get_label_text('result')
        assert text == self.obj.config.EVT_DETAIL_TABLE_TEXT_RESULT

        text = self.obj.get_label_text('video')
        assert text == self.obj.config.EVT_DETAIL_TABLE_TEXT_VIDEO

        text = self.obj.get_label_text('audio')
        assert text == self.obj.config.EVT_DETAIL_TABLE_TEXT_AUDIO

        text = self.obj.get_label_text('transcript')
        assert text == self.obj.config.EVT_DETAIL_TABLE_TEXT_TRANSCRIPT


class TestSettingsPrefix:
    '''Verify that a bogusly defined pupatype complains.
    '''
    class InvalidPupatype:
        def get_pupatype(self):
            return 'cow'

    def setup(self):
        self.prefix = TypePrefix('PUPATYPE', valid_set=VALID_PUPATYPES)
        self.has_pupatype_inst = self.InvalidPupatype()
        self.prefix.inst = self

    def test_invalid_value(self):
        with pytest.raises(ValueError):
            self.prefix.get_prefix()


class TestInvalidPupatypeImpl(PupatypeMixin):
    '''The PupatypeMixin inspect's the class's name to determine
    what pupatype and what viewtype it relates to. If the name
    doesn't contain the expected strings, NotImplementedError is
    supposed to get raised. This test checks that it does.
    '''
    def test_notimplemented_pupatype(self):
        with pytest.raises(NotImplementedError):
            self.get_pupatype()

    def test_notimplemented_viewtype(self):
        with pytest.raises(NotImplementedError):
            self.get_viewtype()

    def get_pupatype_prefix(self):
        del self.get_component_prefix
        del self.get_viewtype_prefix
        return 'cow'

    def test_prefix_fallback(self):
        '''If not get_viewtype_prefix or get_component_prefix is
        defined, the get_pupatype_prefix result should be returned.
        '''
        with pytest.raises(NotImplementedError):
            assert self.get_prefix() == self.get_pupatype_prefix()