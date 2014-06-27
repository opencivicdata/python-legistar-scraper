import re
from collections import defaultdict

from  visitors import Visitor

from legistar.base import Base
from legistar.fields import ElementAccessor


class Visitor(Base, Visitor):
    '''Visits a detail page and collects all the displayed fields into a
    dictionary that maps label text to DOM nodes.

    Effectively groups different elements and their attributes by the unique
    sluggy part of their verbose aspx id names. For example, the 'Txt' part
    of 'ctl00_contentPlaceholder_lblTxt'.
    '''
    # ------------------------------------------------------------------------
    # These methods customize the visitor.
    # ------------------------------------------------------------------------
    def __init__(self):
        self.data = defaultdict(dict)

    def finalize(self):
        '''Reorganize the data so it's readable labels (viewable on the page)
        are the dictionary keys, instead of the sluggy text present in their
        id attributes. Wrap each value in a DetailField.
        '''
        newdata = defaultdict(list)
        for id_attr, data in tuple(self.data.items()):
            alias = data.get('label', id_attr).strip(':')
            value = self.cfg.make_child(ElementAccessor, data['el'])
            newdata[alias].append(value)
            if alias != id_attr:
                newdata[id_attr].append(value)
        return newdata

    def get_nodekey(self, el):
        '''We're visiting an lxml.html doc, so dispatch based on the tag.
        '''
        # The weird Comment tag.
        tag = el.tag
        if not isinstance(tag, str):
            raise self.Continue()
        return tag

    def get_children(self, el):
        return tuple(el)

    # ------------------------------------------------------------------------
    # The DOM visitor methods.
    # ------------------------------------------------------------------------
    def visit_a(self, el):
        attrib = el.attrib
        if 'id' not in attrib:
            return

        # If it's a field label, collect the text and href.
        matchobj = re.search(r'_hyp(.+)', attrib['id'])
        if matchobj:
            key = matchobj.group(1)
            data = self.data[key]
            data.update(el=el)
            if 'label' not in data:
                label = el.text_content().strip(':')
                raise self.Continue()
            return

    def visit_span(self, el):
        idattr = el.attrib.get('id')
        if idattr is None:
            return

        # If it's a label
        matchobj = re.search(r'_lbl(.+?)X', idattr)
        if matchobj:
            key = matchobj.group(1)
            label = el.text_content().strip(':')
            self.data[key]['label'] = label
            return

        matchobj = re.search(r'_lbl(.+)', idattr)
        if matchobj:
            key = matchobj.group(1)
            self.data[key]['el'] = el
            return

        # If its a value
        matchobj = re.search(r'_td(.+)', idattr)
        if matchobj:
            key = matchobj.group(1)
            self.data[key]['el'] = el

    def visit_td(self, el):
        idattr = el.attrib.get('id')
        if idattr is None:
            return
        matchobj = re.search(r'_td(.+)', idattr)
        if matchobj is None:
            return
        key = matchobj.group(1)
        self.data[key]['el'] = el

    def visit_img(self, el):
        _id = el.attrib.get('id')
        if _id is None:
            return
        if '_img' in _id:
            _, key = _id.split('_img')
            self.data[key]['el'] = el