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

    def get_field_data(self, label_text):
        key = self.get_label_text(label_text)
        try:
            return self.field_data[key]
        except KeyError:
            # The data wasn't found, so we skip it.
            raise self.SkipItem()

    def get_field_text(self, label_text):
        field_data = self.get_field_data(label_text)
        if field_data is not None:
            if field_data.is_blank():
                return
            return field_data.get_text()

    def get_field_url(self, label_text):
        field_data = self.get_field_data(label_text)
        if field_data is not None:
            return field_data.get_url() or None


class DetailField(FieldAccessor):
    '''Support the field accessor interface same as TableCell.
    '''
    def __init__(self, data):
        self.data = data

    @property
    def node(self):
        return self.data['node']

    def get_text(self):
        text = get_text(self.node)
        if not self._is_blank(text):
            return text

    def get_url(self):
        for descendant in self.node.find():
            if 'href' in descendant:
                return descendant['href']

    def _is_blank(self, text):
        if not text:
            return True
        if text == 'Not available':
            return True

    def is_blank(self):
        return self._is_blank(self.text)

    def get_mimetype(self):
        key = None
        # First try looking for mimetype gif.
        for descendant in self.node.parent.find().filter(tag='img'):
            if 'src' not in descendant:
                continue
            gif_url = descendant['src']
            path = urlparse(gif_url).path
            if gif_url:
                key = path
        # Fall back to url filename ext.
        if key is None:
            _, extension = self.get_url().rsplit('.', 1)
            key = extension
        return self.cfg.gif_mimetypes.get(key.lower())

    def get_video_url(self):
        key = self.get_label_text('video')
        field_data = self.field_data[key]
        onclick = field_data.data['node']['onclick']
        matchobj = re.search(r"\Video.+?\'", onclick)
        if matchobj:
            return matchobj.group()