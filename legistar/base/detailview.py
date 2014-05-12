import contextlib
from urllib.parse import urlparse, parse_qs, urljoin
from collections import namedtuple, OrderedDict, defaultdict

import visitors
import visitors.ext.etree
from hercules import CachedAttr

from legistar.base.view import View


class DetailView(View):

    @CachedAttr
    def field_data(self):
        G = visitors.ext.etree.from_html(self.doc)
        return DetailVisitor(self.cfg).visit(G)

    def asdict(self):
        raise NotImplemented()


class DetailVisitor(visitors.Visitor):
    '''Visits a detail page and collects all the displayed fields into a
    dictionary mapping label text to values; text if it's a text field,
    text and an href for links, etc.

    Effectively groups different elements and their attributes by the unique
    sluggy part of their verbose aspx id names. For example, the 'Txt' part
    of 'ctl00_contentPlaceholder_lblTxt'.
    '''
    # ------------------------------------------------------------------------
    # These methods customize the visitor.
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
            value = DetailField(data, self.cfg)
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
    def visit_a(self, node):
        if 'id' not in node:
            return
        if 'href' not in node:
            return

        # If it's a field label, collect the text and href.
        matchobj = re.search(r'_hyp(.+)', node['id'])
        if matchobj:
            key = matchobj.group(1)
            data = self.data[key]
            data.update(url=node['href'], node=node)
            if 'label' not in data:
                label = TextRenderer().visit(node).strip().strip(':')
                data['label'] = label
            return

    def visit_span(self, node):
        if 'id' not in node:
            return

        # If it's a label
        matchobj = re.search(r'_lbl(.+?)X', node['id'])
        if matchobj:
            key = matchobj.group(1)
            label = node.children[0]['text'].strip().strip(':')
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

    @contextlib.contextmanager
    def generic_visit(self, node):
        # Add a space if we're writing to an in-progress buffer.
        if self.buf.getvalue():
            self.buf.write(' ')
        # Write in this node's text.
        self.buf.write(node.get('text', '').strip())
        # Allow the visitor to do the same for this node's children.
        yield
        # Now write in this node's tail text.
        self.buf.write(node.get('tail', '').strip())
        # Don't visit children--already visited them above.
        raise self.Continue()

    def finalize(self):
        text = self.buf.getvalue()
        text = text.replace('\xa0', ' ')
        return text


class DetailField:
    '''Support the field accessor interface same as TableCell.
    '''
    def __init__(self, data, config_obj):
        self.data = data
        self.cfg = config_obj

    @property
    def node(self):
        return self.data['node']

    @property
    def text(self):
        if self.is_blank():
            return
        return TextRenderer().visit(self.node)

    @property
    def url(self):
        for descendant in self.node.find():
            if 'href' in descendant:
                return descendant['href']

    def is_blank(self):
        if self.text.strip().replace('\xa0', ' ') == 'Not available':
            return True

    @property
    def mimetype(self):
        for descendant in self.node.find().filter(tag='img'):
            if 'src' not in descendant:
                continue
            gif_url = descendant['src']
            path = urlparse(gif_url).path
            if gif_url is None:
                return
            mimetypes = {
                self.cfg.MIMETYPE_GIF_PDF: 'application/pdf',
            }
            mimetype = mimetypes[path]
            return mimetype
