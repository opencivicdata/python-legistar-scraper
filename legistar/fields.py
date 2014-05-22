import io
import re
from datetime import datetime
from urllib.parse import urlparse

from legistar.base import Base, CachedAttr
from legistar.utils.itemgenerator import make_item, gen_items, ItemGenerator


class FieldAccessor(Base):
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

    def get_img_src(self):
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


class FieldAggregator(Base, ItemGenerator):
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
        try:
            return self.get_config_value(key)
        except:
            self.info('No field %s found on %r. Skipping.', key, self)
            raise self.SkipItem()

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

    def get_aggregator_func_data(self, data):
        '''Return a sequence of (key, value) pairs, where key and
        value are produced by a method on the jurisdiction Config subtype:

        class MyJxn(Config):
            ...
            @make_item('person.' + key)
            def get_person_party(self, data):
                value = data.get('something')
                return value

        I conceded that this is badly named.
        '''
        config = self.config
        pupatype = self.PUPATYPE
        pupatype_aggregator_funcs = config.aggregator_funcs[pupatype]
        for unbound_method in pupatype_aggregator_funcs:
            yield unbound_method(config, data)


class ElementAccessor(FieldAccessor):
    '''Provides access to text, url, etc., on DOM elements from the
    lxml.html doc.
    '''
    def __init__(self, el):
        self.el = el

    def get_url(self):
        for xpath in ('string(@href)', 'string(.//a/@href)'):
            url = self.el.xpath(xpath)
            if url:
                return url

    def get_text(self):
        '''This is necessary to prevent idiocy of el.text_content()
        which sometimes doesn't add spaces.
        '''
        buf = io.StringIO()
        first = True
        for chunk in self.el.itertext():
            chunk = chunk.strip()
            if not chunk:
                continue
            if not first:
                buf.write(' ')
            buf.write(chunk)
            first = False
        text = buf.getvalue().strip()
        if not self._is_blank(text):
            return text

    def _is_blank(self, text):
        if not text:
            return True
        if text.strip().replace('\xa0', ' ') == 'Not available':
            return True

    def is_blank(self):
        return self._is_blank(self.text)

    def get_mimetype(self):
        gif_url = None
        for xpath in ('string(.//img/@src)', 'string(..//img/@src)'):
            gif_url = self.el.xpath(xpath)
            if gif_url:
                break
        if gif_url:
            path = urlparse(gif_url).path
            key = path
        else:
            _, extension = self.get_url().rsplit('.', 1)
            key = extension
        return self.cfg.mimetypes.get(key.lower())

    def get_img_src(self):
        '''Returns the first string in the field data.
        '''
        return self.el.attrib.get('src')

    def get_video_url(self):
        raise NotImplementedError()
