import re
import logging
from io import StringIO
from operator import itemgetter
from collections import defaultdict

import lxml.html
import requests

from visitors import Visitor
from rexlex import Lexer, bygroups, include
from hercules import CachedAttr, NoClobberDict, SetDefault
from hercules.trie import Trie
from hercules.tokentype import Token
from treebie.syntaxnode import tokenseq, token_subtypes, SyntaxNode as Node


class TelerikInvokLexer(Lexer):
    """Lex Telerik Javascript invocation garbage.
    """

    re_skip = re.compile('\s+')
    js_identifier = r'(?i)[\$_A-Z][\$_A-Z\d]+'
    tokendefs = {
        # --------------------------------------------------------------------
        # Parse each js control invocation.
        # --------------------------------------------------------------------
        'root': [
            ('Cdata', r'//\<!\[CDATA\['),
            ('NewControl', r'Sys.Application.add_init\(function\(\) \{', 'new_control'),
            ('JsGarbage', r'WebForm_InitCallback\(\);'),
        ],

        # Parses the beginning of function calls the create form controls.
        'new_control': [
            ('Control.Create', r'\$create\(', 'invok'),
            ('Control.End', r'\}\);', '#pop')
        ],

        # Parses the form control invocation.
        'invok': [
            (bygroups('Control.Type'), r'Telerik.Web.UI.([A-Za-z\d_]+), '),
            include('json_data'),
            ('Invok.Null', r'null'),
            ('Invok.Comma', r','),
            (bygroups('Control.Selector'), r'\$get\("(.{,255})"\)'),
            ('Invok.End', r'\);', '#pop'),
        ],

        # --------------------------------------------------------------------
        # Parse the arg json.
        # --------------------------------------------------------------------
        'json_data': [
            ('Brace.Open', '\{', 'object'),
            ('Bracket.Open', '\[', 'array'),
            ],

        'js_identiers': [
            ('Identifier', js_identifier),
            ],

        'object': [
            include('object.item'),
            ('Brace.Close', '\}', '#pop'),
            ],

        'object.item': [
            include('object.item.key'),
            ],

        'object.item.key': [
            (bygroups('Key'), r'"([^\\]+?)"\s*:', 'object.item.value'),
            (bygroups('Key'), r'(%s)\s*:' % js_identifier, 'object.item.value'),
            ],

        'object.item.value': [
            include('json_data'),
            include('literals'),
            include('js_identiers'),
            ('Comma', ',', '#pop'),
            ],

        'array': [
            include('array.item'),
            ('Bracket.Close', r'\]', '#pop'),
            ],

        'array.item': [
            include('json_data'),
            include('literals'),
            include('js_identiers'),
            ('Comma', ','),
            ],

        'literals': [
            ('Literal.Number.Real', '\d+\.\d*'),
            ('Literal.Number.Int', '\d+'),
            ('Quote.Open', r'"', 'string'),
            ('Literal.Bool', '(?:true|false)'),
            ('Literal.Null', 'null'),
            ],

        'string': [
            ('Literal.String', r'\\"'),
            ('Literal.String', r'[^\\"]+'),
            (bygroups('Literal.Unichr'), r'\\u(\d+)'),
            ('Quote.Close', r'"', '#pop'),
            ]
    }


class Root(Node):

    @tokenseq('Cdata')
    def handle_cdata(self, *items):
        return self

    @tokenseq('JsGarbage')
    def handle_js_garbage(self, *items):
        return self

    @tokenseq('NewControl')
    def start_control(self, *items):
        return self.descend(TelerikControl)


class TelerikControl(Node):
    '''A javascript form control.
    '''
    @tokenseq('Control.End')
    def handle_end(self, *items):
        return self

    @tokenseq('Control.Create', 'Control.Type')
    def handle_new(self, *items):
        return self.descend(TelerikControlType, *items[1:])

    @tokenseq('Brace.Open')
    def handle_brace(self, *items):
        invok = self.descend(TelerikControlInvok)
        root = invok.descend(JsonRoot)
        return root.start_object(*items)


class TelerikControlType(Node):
    '''The type of form control, like 'RadTabStrip'.
    '''


class TelerikControlSelector(Node):
    '''The id of the element were this particular control can be found.
    '''


class TelerikControlInvok(Node):

    # ------------------------------------------------------------------------
    # Skip all this crap.
    @tokenseq('Invok.Comma')
    def handle_comma(self, *items):
        return self

    @tokenseq('Invok.Null')
    def handle_null(self, *items):
        self.descend('JsNull')
        return self

    @tokenseq('Control.Selector')
    def handle_selector(self, selector):
        return self.descend(TelerikControlSelector, selector)

    @tokenseq('Invok.End')
    def handle_end(self, *items):
        return self


class JsonRoot(Node):

    @tokenseq('Brace.Open')
    def start_object(self, *items):
        obj = self.descend(Object)
        return obj.descend(ObjectItem)

    @tokenseq('Bracket.Open')
    def start_array(self, *items):
        return self.descend(Array)

    @tokenseq('Brace.Close')
    def finish_object(self, *items):
        return self.popstate()

    @tokenseq('Bracket.Close')
    def finish_array(self, *items):
        return self.popstate()

    def decode(self):
        return next(iter(self.children)).decode()


class Value(JsonRoot):

    @tokenseq('Quote.Open', 'Literal.String')
    def handle_str(self, quote, string):
        return self.descend(String, string)

    @tokenseq('Quote.Open', 'Quote.Close')
    def handle_empty_string(self, *items):
        return self.descend(String)

    @token_subtypes('Literal')
    def handle_literal(self, *items):
        return self.descend(Literal, *items).popstate()


class Object(Node):

    @tokenseq('Comma')
    def end_item(self, *items):
        return self.descend(ObjectItem)

    @tokenseq('Brace.Close')
    def end_object(self, *items):
        return self.popstate()

    def decode(self):
        res = {}
        return dict(node.decode() for node in self.children if node.children)


class ObjectItem(Node):

    @tokenseq('Key')
    def handle_key(self, *items):
        self.descend(ItemKey, *items)
        return self.descend(ItemValue)

    def decode(self):
        for node in self.children:
            yield node.decode()


class ItemKey(Node):

    def decode(self):
        return self.first_text()


class ItemValue(Value):

    @token_subtypes('Literal')
    def handle_literal(self, *items):
        return self.descend(Literal, *items).popstate()

    def decode(self):
        for node in self.children:
            return node.decode()


class Array(Value):

    @tokenseq('Comma')
    def ignore_comma(self, *items):
        return self

    def decode(self):
        return [node.decode() for node in self.children]


class Literal(Node):

    to_json = {
        'Literal.Number.Real': float,
        'Literal.Number.Int': int,
        'Literal.Bool': lambda s: s == 'true',
        'Literal.Null': lambda s: None,
        'Literal.String': lambda s: s,
        'Literal.Unichr': lambda s: chr(int(s))}

    def decode(self):
        first = self.first()
        func = self.to_json[first.token]
        return func(first.text)


class String(Node):

    @tokenseq('Literal.String')
    def handle_str(self, *items):
        return self.extend(items)

    @tokenseq('Quote.Close')
    def end_str(self, *items):
        return self.popstate()

    @tokenseq('Literal.Unichr')
    def handle_unicode_escape(self, *items):
        return self.extend(items)

    def decode(self):
        buf = StringIO()
        for tok in self.tokens:
            buf.write(tok.text)
        return buf.getvalue()


class ControlObj:
    def __repr__(self):
        tmpl = '<%s: %s %s at %s>'
        vals = (
            self.__class__.__name__, self.type, self.selector, id(self))
        return tmpl % vals

    @property
    def initdata(self):
        return self.invok[0]


class ControlInvokObj(list):
    pass


class JsNullObj:
    pass


class TelerikSpecRenderer(Visitor):

    def __init__(self):
        self.controls = []
        self.widgets = []

    def visit_TelerikControl(self, node):
        control_obj = ControlObj()
        self.controls.append(control_obj)
        node.ctx['control'] = control_obj

    def visit_TelerikControlSelector(self, node):
        node.ctx['control'].selector = node.first_text()

    def visit_TelerikControlType(self, node):
        node.ctx['control'].type = node.first_text()

    def visit_TelerikControlInvok(self, node):
        node.ctx['control'].invok = ControlInvokObj()

    def visit_JsonRoot(self, node):
        data = node.decode()
        control_obj = node.ctx['control']
        control_obj.invok.append(data)
        if 'clientStateFieldID' in data:
            self.widgets.append(control_obj)

    def visit_JsNull(self, node):
        node.ctx['control'].invok.append(None)


class LegistarSite:
    '''This object gets a root Legislator url and has to figure what view
    the homepage is displaying, then figure out where the advanced search
    page is, meetings, committees, etc.
    '''
    def __init__(self, legistar_root_url):
        self.root_url = legistar_root_url

    def lxmlize(self, url):
        resp = requests.get(url)
        doc = lxml.html.fromstring(resp.text)
        doc.make_links_absolute(url)
        return doc

    @CachedAttr
    def doc(self):
        # return self.lxmlize(self.root_url)
        return lxml.html.parse('nychome.html')

    def _get_telerik_js(self):
        for script in self.doc.xpath('//script'):
            if script.text is None:
                continue
            if 'WebForm_InitCallback' in script.text:
                return script.text

    @CachedAttr
    def _telerik_ui_meta(self):
        text = self._get_telerik_js()
        import pdb; pdb.set_trace()
        lexer = TelerikInvokLexer(text)
        root = Root().parse(lexer)
        visitor = TelerikSpecRenderer()
        visitor.visit(root)
        return visitor

    @CachedAttr
    def widgets(self):
        return self._telerik_ui_meta.widgets

    @CachedAttr
    def controls(self):
        return self._telerik_ui_meta.controls




if __name__ == '__main__':

    nyc = 'http://legistar.council.nyc.gov/Calendar.aspx'
    site = LegistarSite(nyc)
    widgets = site.widgets

    # doc = lxml.html.parse('advanced_search.html')
    # text = doc.xpath('//script')[0].text
    # lexer = TelerikInvokLexer(text)
    # root = Root().parse(lexer)
    # ui = TelerikSpecRenderer()
    # ui.visit(root)
    import pdb; pdb.set_trace()