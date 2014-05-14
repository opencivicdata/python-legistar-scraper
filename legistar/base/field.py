import re
from datetime import datetime

from hercules import CachedAttr

from legistar.base.ctx import CtxMixin
from legistar.utils.itemgenerator import make_item, ItemGenerator


class FieldAccessor(CtxMixin):
    '''This class defines a minimal interface subclasses will implement.
    '''
    def get_url(self):
        '''Returns the first url in the field data.
        '''
        raise NotImplementedError()

    def gen_urls(self):
        '''A generator of all urls in the field data.
        '''
        raise NotImplementedError()

    def get_text(self):
        '''Returns the first string in the field data.
        '''
        raise NotImplementedError()

    @CachedAttr
    def text(self):
        '''Text can be slightly expensive.
        '''
        return self.get_text()

    def gen_text(self):
        '''A generator of all strings in the field data.
        '''
        raise NotImplementedError()

    def is_blank(self):
        raise NotImplementedError()

    def get_mimetype(self):
        raise NotImplementedError()


class FieldAggregator(ItemGenerator, CtxMixin):
    '''This class provides some plumbing for accessing the appropriate
    config values. It's __iter__ method generates a list of 2-tuples,
    so to convert it to a dict, it's just dict(instance).
    '''
    @property
    def KEY_PREFIX(self):
        '''The "EVT_TABLE" part of self.cfg.EVT_TABLE_TEXT_TOPIC.
        '''
        msg = 'Field subclasses must define KEY_PREFIX.'
        raise NotImplementedError(msg)

    def get_config_value(self, key):
        '''Get a value with the class's key prefix.
        '''
        name = '%s_%s' % (self.KEY_PREFIX, key.upper())
        return getattr(self.cfg, name)

    def get_label_text(self, key):
        '''Get field label text using the class's prefix:

        self.get_label_text('topic') --> self.cfg.EVT_TABLE_TEXT_TOPIC
        '''
        key = 'TEXT_%s' % key.upper()
        return self.get_config_value(key)
