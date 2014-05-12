import re
import sys
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



class StatementsLexer(Lexer):
    """Lex Telerik Javascript invocation garbage.
    """
    js_identifier = r'(?i)[\$_A-Z][\$_A-Z\d\.]+'

    raise_incomplete = True
    re_skip = re.compile('\s+')
    tokendefs = {
        # --------------------------------------------------------------------
        # Parse each js control invocation.
        # --------------------------------------------------------------------
        'root': [
            ('CData.Open', r'//\<!\[CDATA\['),
            include('statements'),
            ('CData.Close', r'//\]\]>'),
        ],
        'statements': [
            include('value'),
            ('SemiColon', ';\s*'),
        ],

        # --------------------------------------------------------------------
        # Parse the arg json.
        # --------------------------------------------------------------------
        'value': [
            include('containers'),
            include('literals'),
            include('lambda'),
            include('identiers'),
            ],

        'invocation': [
            include('value'),
            ('Comma', r','),
            ('Invok.End', r'\)', '#pop'),
            ],

        'containers': [
            ('Brace.Open', '\{', 'object'),
            ('Bracket.Open', '\[', 'array'),
            ],

        'lambda': [
            ('Lambda', 'function', 'lambda_def'),
            ],

        'lambda_def': [
            ('Lambda.Signature.Start', r'\(', 'lambda_signature'),
            ('Lambda.Body.Start', '\{', 'lambda_body'),
            ],

        'lambda_signature': [
            include('identiers'),
            ('Comma', r','),
            ('Lambda.Signature.End', '\)', '#pop'),
            ],

        'lambda_body': [
            include('statements'),
            ('Lambda.Body.End', '\}', '#pop'),
            ],

        'identiers': [
            ('Identifier', js_identifier),
            ('Invok.Start', r'\(', 'invocation'),
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
            include('value'),
            ('Comma', ',', '#pop'),
            ],

        'array': [
            include('array.item'),
            ('Bracket.Close', r'\]', '#pop'),
            ],

        'array.item': [
            include('value'),
            ('Comma', ','),
            ],

        'literals': [
            ('Literal.Number.Real', '\d+\.\d*'),
            ('Literal.Number.Int', '\d+'),
            ('Quote.Open', r'"', 'dq_string'),
            ('Quote.Open', r"'", 'sq_string'),
            ('Literal.Bool', '(?:true|false)'),
            ('Literal.Null', 'null'),
            ],

        'dq_string': [
            ('Literal.String', r'\\"'),
            ('Literal.String', r'[^\\"]+'),
            ('Literal.String.Unichr', r'\\u\d+'),
            # Escaped escape chars.
            ('Literal.String', r'\\\\u(\d+)'),
            ('Literal.String', r'\\\\r\\\\n'),
            ('Quote.Close', r'"', '#pop'),
            ],

        'sq_string': [
            ('Literal.String', r"\\'"),
            ('Literal.String', r"[^\\']+"),
            ('Literal.String.Unichr', r'\\u\d+'),
            # Escaped escape chars.
            ('Literal.String', r'\\\\u(\d+)'),
            ('Literal.String', r'\\\\r\\\\n'),
            ('Quote.Close', r"'", '#pop'),
            ],
    }


class Statements(Node):
    '''One or more js statements.
    '''
    @token_subtypes('CData')
    def handle_cdata(self, *items):
        return self

    @token_subtypes('Identifier')
    def handle_identifier(self, *items):
        statement = self.descend(Statement)
        return statement.descend(Identifier, *items)


class Statement(Node):
    '''A single JS statement.
    '''
    @tokenseq('SemiColon')
    def end(self, *items):
        return self.popstate()


class Identifier(Node):
    '''A single js identifier.
    '''
    @tokenseq('Invok.Start')
    def start_invok(self, *items):
        return self.descend(Invocation)


class Containers(Node):

    @tokenseq('Brace.Open')
    def start_object(self, *items):
        return self.descend_path(Object)

    @tokenseq('Bracket.Open')
    def start_array(self, *items):
        return self.descend(Array)


class Literals(Node):

    @tokenseq('Comma')
    def handle_comma(self, *items):
        return self

    @token_subtypes('Literal')
    def handle_literal(self, *items):
        return self.descend(Literal, *items)

    @token_subtypes('Literal.String')
    def handle_string(self, *items):
        return self.descend(String, *items)

    order = [handle_string, handle_literal, handle_comma]

class Value(Containers, Literals):

    @tokenseq('Quote.Open', 'Literal.String')
    def handle_str(self, quote, string):
        return self.descend(String, string)

    @tokenseq('Quote.Open', 'Literal.String.Unichr')
    def handle_unichr(self, quote, string):
        return self.descend(String, string)

    @tokenseq('Quote.Open', 'Quote.Close')
    def handle_empty_string(self, *items):
        return self.descend(String)


class Invocation(Value):

    @tokenseq('Lambda')
    def start_lambda(self, *items):
        return self.descend(Lambda)

    @tokenseq('Invok.End')
    def handle_end(self, *items):
        return self.popstate()

    @tokenseq('Identifier')
    def handle_identifier(self, *items):
        return self.descend(Identifier, *items)


class Lambda(Node):

    @tokenseq('Lambda.Signature.Start')
    def start_signature(self, *items):
        return self.descend(LambdaSignature)

    @tokenseq('Lambda.Body.Start')
    def start_body(self, *items):
        return self.descend(LambdaBody)


class LambdaSignature(Node):

    @tokenseq('Lambda.Signature.End')
    def end_signature(self, *items):
        return self.popstate()

class LambdaBody(Statements):

    @tokenseq('Lambda.Body.End')
    def start_body(self, *items):
        return self.popstate()


class Object(Node):

    @tokenseq('Key')
    def handle_identifier(self, *items):
        object_item = self.descend(ObjectItem)
        key = object_item.descend(ItemKey, *items)
        return object_item.descend(ItemValue)

    @tokenseq('Brace.Close')
    def end_object(self, *items):
        return self.popstate()

    def decode(self):
        return dict(tuple(node.decode()) for node in self.children if node.children)


class ObjectItem(Node):

    @tokenseq('Key')
    def handle_key(self, *items):
        '''This is a tad awkward. Encountering a key here means this item
        is done and we should start a new one.
        '''
        object_item = self.parent.descend(ObjectItem)
        key = object_item.descend(ItemKey, *items)
        return object_item.descend(ItemValue)

    def decode(self):
        key, val = self.children
        return (key.decode(), val.decode())


class ItemKey(Node):

    def decode(self):
        return self.first_text()


class ItemValue(Value):

    def decode(self):
        for node in self.children:
            return node.decode()


class Array(Value):

    @tokenseq('Bracket.Close')
    def end(self, *items):
        return self.popstate()

    def decode(self):
        return [node.decode() for node in self.children]


class Literal(Node):

    to_json = {
        'Literal.Number.Real': float,
        'Literal.Number.Int': int,
        'Literal.Bool': lambda s: s == 'true',
        'Literal.Null': lambda s: None}

    def decode(self):
        first = self.first()
        func = self.to_json[first.token]
        return func(first.text)


class String(Node):

    def parse_unicode_escape(s):
        return bytes(s, 'ascii').decode('unicode-escape')

    to_json = {
        'Literal.String': lambda s: s,
        'Literal.String.Unichr': parse_unicode_escape}

    def decode(self):
        first = self.first()
        func = self.to_json[first.token]
        return func(first.text)

    @tokenseq('Literal.String')
    def handle_str(self, *items):
        return self.extend(items)

    @tokenseq('Quote.Close')
    def end_str(self, *items):
        return self.popstate()

    @tokenseq('Literal.String.Unichr')
    def handle_unicode_escape(self, *items):
        return self.extend(items)

    def decode(self):
        buf = StringIO()
        for tok in self.tokens:
            func = self.to_json[tok.token]
            text = func(tok.text)
            buf.write(text)
        return buf.getvalue()


# ---------------------------------------------------------------------------
class WidgetMetadata:

    def __init__(self, invocation_node):
        self.node = invocation_node

    def __repr__(self):
        tmpl = '<%s: %s %s at %s>'
        vals = (
            self.__class__.__name__, self.type, self.selector, id(self))
        return tmpl % vals

    @property
    def type(self):
        return self.node.children[0].first_text()

    @CachedAttr
    def initdata(self):
        return self.node.children[1].decode()

    @property
    def selector(self):
        return self.node.children[-1].find_one('String').first_text()


class TelerikSniffer(Visitor):

    def __init__(self):
        self.widgets = []

    def visit_Invocation(self, node):
        if node.parent.first_text() == '$create':
            widget = WidgetMetadata(node)
            self.widgets.append(widget)
            node.ctx['control'] = widget


class Widget:

    def __init__(self, metadata, lxml_doc):
        self.metadata = metadata
        self.doc = lxml_doc

    @property
    def initdata(self):
        return self.metadata.initdata

    @property
    def selector(self):
        return self.metadata.selector

    @property
    def clientstate_id(self):
        return self.initdata['clientStateFieldID']

    @property
    def clientstate_element(self):
        xpath = '//*[@id="%s"]' % self.clientstate_id
        return self.doc.xpath(xpath).pop()

    @property
    def doc_element(self):
        '''The element in the doc where this widget is found.
        '''
        xpath = '//*[@id="%s"]' % self.selector
        return self.doc.xpath(xpath).pop()


class RadTabStrip(Widget):

    @property
    def selected_index(self):
        return self.initdata['_selectedIndex']

    def _gen_tabs(self):
        links = self.doc_element.xpath('.//a')
        urls = [a.attrib['href'] for a in links]
        text = [a.text_content() for a in links]
        metanames = [obj['value'] for obj in self.initdata['tabData']]
        for tabdata in zip(metanames, urls, text):
            yield dict(zip(('metaname', 'url', 'text'), tabdata))

    @CachedAttr
    def tabs(self):
        return list(self._gen_tabs())

    @property
    def active_tab(self):
        return self.tabs[self.selected_index]


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
        print('fetching')
        # return self.lxmlize(self.root_url)
        return lxml.html.parse('nychome.html').getroot()
        # return lxml.html.parse('nychome.html')

    def _get_widget_js(self):
        '''Returns the text of the Telerik widget js element.
        '''
        for script in self.doc.xpath('//script'):
            if script.text is None:
                continue
            if 'Sys.Application.add_init' in script.text:
                return script.text
        raise Exception('No Telerik JS elements found.')

    def _get_widget_metadata(self):
        text = self._get_widget_js()
        lexer = StatementsLexer(text)
        print('parsing widgets')
        root = Statements().parse(lexer)
        visitor = TelerikSniffer()
        visitor.visit(root)
        return visitor.widgets

    def _gen_widgets(self):
        this_module = sys.modules[__name__]
        for metadata in self._get_widget_metadata():
            _, _, cls_name = metadata.type.rpartition('.')
            widget_cls = getattr(this_module, cls_name, Widget)
            yield widget_cls(metadata, self.doc)

    @CachedAttr
    def widgets(self):
        return list(self._gen_widgets())

    @property
    def tabs(self):
        return self.widgets[0].tabs

    def get_active_tab(self):
        return self.widgets[0].active_tab

    def navigate_to_page(self, type_):
        '''Call with 'bills', 'events', or 'committees'
        '''
        tabtext = self.tabtext[type_]
        for tab in self.tabs:
            if tab['text'] == tabtext:
                break
        url = tab['url']
        import pdb; pdb.set_trace()



class NycLegistar(LegistarSite):

    tabtext = {
        'bills': 'Legislation',
        'events': 'Calendar',
        'committees': 'Committees',
        }

    ADVANCED_SEARCH_TEXT = 'Advanced Search >>>'


class LegislationSearch:

    SIMPLE_SEARCH_TEXT = '<<< Simple Search'
    ADVANCED_SEARCH_TEXT = 'Detailed Search >>>'

    def __init__(self, url):
        self.url = url

    def is_advanced(self):
        return self.SIMPLE_SEARCH_TEXT in self.text

    def is_simple(self):
        return self.ADVANCED_SEARCH_TEXT in self.text


from visitors.ext.etree import LxmlHtmlVisitor

class PageVisitor(LxmlHtmlVisitor):

    LABEL_STRING = 'ctl00_ContentPlaceHolder1_lbl'
    def generic_visit(self, el):
        if self.LABEL_STRING in el.attrib.get('id', ''):
            import pdb; pdb.set_trace()



if __name__ == '__main__':

    nyc = 'http://legistar.council.nyc.gov/'
    site = NycLegistar(nyc)
    site.widgets[5].initdata
    import pdb; pdb.set_trace()
    import pprint
    pprint.pprint(site.tabs)
    x = PageVisitor().visit(site.doc.getroot())
    import pdb; pdb.set_trace()
    site.navigate_to_page('bills')

#     text = '''
# Telerik.Web.UI.RadScheduler._preInitialize("ctl00_ContentPlaceHolder1_RadScheduler1",0,0,2,false);WebForm_AutoFocus('ctl00_ContentPlaceHolder1_txtSearch');Sys.Application.add_init(function() {
#     $create(Telerik.Web.UI.RadTabStrip, {"_selectedIndex":2,"_skin":"Default","causesValidation":false,"clickSelectedTab":true,"clientStateFieldID":"ctl00_tabTop_ClientState","selectedIndexes":["2"],"tabData":[{"value":"Home"},{"value":"Legislation"},{"value":"Calendar"},{"value":"MainBody"},{"value":"Departments"}]}, null, null, $get("ctl00_tabTop"));
# });
# Sys.Application.add_init(function() {
#     $create(Telerik.Web.UI.RadAjaxManager, {"_updatePanels":"\\u0026","ajaxSettings":[{InitControlID : "ctl00_ContentPlaceHolder1_gridCalendar",UpdatedControls : [{ControlID:"ctl00_ContentPlaceHolder1_gridCalendar",PanelID:"ctl00_ContentPlaceHolder1_RadAjaxLoadingPanel1"}]},{InitControlID : "ctl00_ContentPlaceHolder1_RadScheduler1",UpdatedControls : [{ControlID:"ctl00_ContentPlaceHolder1_RadScheduler1",PanelID:"ctl00_ContentPlaceHolder1_RadAjaxLoadingPanel1"}]}],"clientEvents":{OnRequestStart:"",OnResponseEnd:""},"defaultLoadingPanelID":"","enableAJAX":true,"enableHistory":false,"links":[],"styles":[],"uniqueID":"ctl00$ContentPlaceHolder1$RadAjaxManager1","updatePanelsRenderMode":0}, null, null, $get("ctl00_ContentPlaceHolder1_RadAjaxManager1"));
# });
# '''


#     # doc = lxml.html.parse('advanced_search.html')
#     # text = doc.xpath('//script')[0].text
#     # # lexer = TelerikInvokLexer(text, loglevel=5)
#     # lexer = StatementsLexer(text, loglevel=5)
#     lexer = StatementsLexer(text)
#     toks = []
#     for tok in lexer:
#         print(tok)
#         toks.append(tok)
#     root = Statements().parse(toks)
#     ui = TelerikSniffer()
#     ui.visit(root)
#     import pdb; pdb.set_trace()