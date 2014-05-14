import io
import re
import contextlib
from urllib.parse import urlparse
from collections import defaultdict

import visitors
import visitors.ext.etree
from hercules import CachedAttr

from legistar.base.view import View
from legistar.base.field import FieldAggregator, FieldAccessor


class DetailView(View, FieldAggregator):
    VIEWTYPE = 'detail'
    KEY_PREFIX = 'EVT_DETAIL'

    @CachedAttr
    def field_data(self):
        G = visitors.ext.etree.from_html(self.doc)
        return DetailVisitor(self.cfg).visit(G)

    def asdict(self):
        return dict(self)


class DetailVisitor(visitors.Visitor):
    '''Visits a detail page and collects all the displayed fields into a
    dictionary that maps label text to taterized DOM nodes.

    Effectively groups different elements and their attributes by the unique
    sluggy part of their verbose aspx id names. For example, the 'Txt' part
    of 'ctl00_contentPlaceholder_lblTxt'.
    '''
    # ------------------------------------------------------------------------
    # These methods customize the visitor.
    # ------------------------------------------------------------------------
    def __init__(self, config_obj):
        self.data = defaultdict(dict)
        self.config_obj = self.cfg = config_obj

    def finalize(self):
        '''Reorganize the data so it's readable labels (viewable on the page)
        are the dictionary keys, instead of the sluggy text present in their
        id attributes. Wrap each value in a DetailField.
        '''
        newdata = {}
        for id_attr, data in tuple(self.data.items()):
            alias = data.get('label', id_attr).strip(':')
            value = self.cfg.make_child(DetailField, data)
            newdata[alias] = value
            if alias != id_attr:
                newdata[id_attr] = value
        return newdata

    def get_nodekey(self, node):
        '''We're visiting a treebie-ized lxml.html document, so dispatch is
        based on the tag attribute.
        '''
        yield node['tag']

    # ------------------------------------------------------------------------
    # The DOM visitor methods.
    # ------------------------------------------------------------------------
    def visit_a(self, node):
        if 'id' not in node:
            return
        if 'href' not in node:
            return

        self.cfg.critical(node['id'])

        # If it's a field label, collect the text and href.
        matchobj = re.search(r'_hyp(.+)', node['id'])
        if matchobj:
            key = matchobj.group(1)
            if key == 'Name':
                import pdb; pdb.set_trace()
            data = self.data[key]
            data.update(url=node['href'], node=node)
            if 'label' not in data:
                label = get_text(node).strip(':')
                data['label'] = label
            return

    def visit_span(self, node):
        if 'id' not in node:
            return

        # If it's a label
        matchobj = re.search(r'_lbl(.+?)X', node['id'])
        if matchobj:
            key = matchobj.group(1)
            label = get_text(node).strip(':')
            self.data[key]['label'] = label
            return

        matchobj = re.search(r'_lbl(.+)', node['id'])
        if matchobj:
            key = matchobj.group(1)
            self.data[key]['node'] = node
            return

        # If its a value
        matchobj = re.search(r'_td(.+)', node['id'])
        if matchobj:
            key = matchobj.group(1)
            self.data[key]['node'] = node

    def visit_td(self, node):
        if 'id' not in node:
            return
        matchobj = re.search(r'_td(.+)', node['id'])
        if matchobj is None:
            return
        key = matchobj.group(1)
        self.data[key]['node'] = node


class TextRenderer(visitors.Visitor):
    '''Render some nesty html text into a string, adding spaces for sanity.
    '''
    def __init__(self):
        self.buf = io.StringIO()

    def scrub_text(self, text):
        return text.replace('\xa0', ' ').strip()

    @contextlib.contextmanager
    def generic_visit(self, node):
        # Add a space if we're writing to an in-progress buffer.
        if self.buf.getvalue():
            self.buf.write(' ')
        # Write in this node's text.
        text = node.get('text', '')
        text = self.scrub_text(text)
        self.buf.write(text)
        # Allow the visitor to do the same for this node's children.
        yield
        # Now write in this node's tail text.
        text = node.get('tail', '')
        text = self.scrub_text(text)
        self.buf.write(text)
        # Don't visit children--already visited them above.
        import pudb; pudb.set_trace()
        raise StopIteration()
        # raise self.Continue()

    def finalize(self):
        text = self.buf.getvalue()
        return text


def get_text(node):
    return TextRenderer().visit(node).strip()


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