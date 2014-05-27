from legistar.base import Base
from legistar.pupatypes import PupatypeMixin
from legistar.jurisdictions.config import NYC


class PeoplePupatype(Base, PupatypeMixin):

    PUPATYPE = 'people'
    VIEWTYPE = 'search'
    COMPONENT_TYPE = 'table'


config = NYC()


class TestPupatypePeople:

    obj = config.make_child(PeoplePupatype)

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


class EventsPupatype(Base, PupatypeMixin):

    PUPATYPE = 'events'
    VIEWTYPE = 'detail'
    COMPONENT_TYPE = 'table'


class TestPupatypeEvents:

    obj = config.make_child(EventsPupatype)

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
