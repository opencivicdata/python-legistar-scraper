import re
import io
import time
import json
import contextlib
from datetime import datetime
from collections import namedtuple, OrderedDict, defaultdict
from urllib.parse import urlparse, parse_qs, urljoin

import lxml.html
import requests
from hercules import CachedAttr
from visitors import Visitor
import visitors.ext.etree


class Client:

    def __init__(self, config_obj):
        self.cfg = config_obj
        self.session = self.cfg.SESSION_CLASS()

        # Silly aspx client state:
        self._event_validation = None
        self._view_state = None
        self._event_target = None
        self._event_argument = None

    def update_state(self, resp):
        doc = lxml.html.fromstring(resp.text)
        form = dict(doc.forms[0].fields)
        self._event_validation = form.get('__EVENTVALIDATION')
        self._view_state = form.get('__VIEWSTATE')
        self._event_target = form.get('__EVENTTARGET')
        self._event_argument = form.get('__EVENTARGUMENT')

    def get(self, url, **kwargs):
        print("GET'ing " + url)
        _kwargs = dict(self.cfg.requests_kwargs)
        _kwargs.update(kwargs)
        resp = self.session.get(url, **kwargs)
        self.update_state(resp)
        return resp

    def post(self, url, data=None, **kwargs):
        print("POST'ing " + url)
        _kwargs = dict(self.cfg.requests_kwargs)
        _kwargs.update(kwargs)
        resp = self.session.post(url, data, **kwargs)
        self.update_state(resp)
        return resp


class View:

    def __init__(self, config_obj, url=None, doc=None):
        self.url = url
        self.doc = doc
        self.config_obj = config_obj

    @property
    def url(self):
        if self._url is None:
            return self.cfg.root_url
        else:
            return self._url

    @url.setter
    def url(self, url):
        self._url = url

    @property
    def doc(self):
        if self._doc is None:
            resp = self.cfg.client.get(self.url)
            doc = lxml.html.fromstring(resp.text)
            doc.make_links_absolute(self.url)
            self._doc = doc
        else:
            doc = self._doc
        return doc

    @doc.setter
    def doc(self, doc):
        self._doc = doc

    @property
    def config_obj(self):
        return self._config_obj

    @config_obj.setter
    def config_obj(self, config_obj):
        '''Config obj needs to be instantiated for descriptors to work.
        '''
        if isinstance(config_obj, type):
            self._config_obj = config_obj()
        else:
            self._config_obj = config_obj

    cfg = config_obj

    def _gen_tabdata(self):
        url_xpath = '//div[@id="ctl00_tabTop"]//a[contains(@class, "rtsLink")]/@href'
        text_xpath = '//div[@id="ctl00_tabTop"]//span[contains(@class, "rtsTxt")]/text()'
        urls = self.doc.xpath(url_xpath)
        text = self.doc.xpath(text_xpath)
        for data in zip(urls, text):
            yield dict(zip(('url', 'text'), data))

    @property
    def tabdata(self):
        return tuple(self._gen_tabdata())

    def get_active_tab(self):
        tabtext = self.doc.xpath(self.cfg.TAB_TEXT_XPATH)
        for tab in self.tabdata:
            if tab['text'] == tabtext:
                return tab


class Root(View):
    '''Here we don't know what the view is.
    '''
    def get_current_tabmeta(self):
        '''Inspect the nav tabs to get metadata for the current tab.
        '''
        current_tab = self.get_active_tab()
        tabmeta = self.cfg.tabs.by_text[current_tab['text']]
        return tabmeta

    def get_current_pupatype(self):
        '''Inspect the current page to determine what pupa type is displayed.
        '''
        tabmeta = self.get_current_tabmeta()
        return tabmeta.pupatype

    def get_pupatype_formclass(self, pupatype):
        '''Get the View subclass defined for each pupa type.
        '''
        return self.cfg.forms.by_pupatype[pupatype]

    def get_pupatype_view(self, pupatype):
        '''Where pupa model is one of 'bills', 'orgs', 'events'
        or 'people', return a matching View subclass.
        '''
        tabmeta = self.cfg.tabs.by_pupatype[pupatype]
        url = urljoin(self.cfg.root_url, tabmeta.path)
        form_meta = self.get_pupatype_formclass(pupatype)
        return form_meta.formtype(self.cfg, url=url)

    def yield_pupatype_objects(self, pupatype):
        '''Given a pupa type, page through the search results and
        yield each object.
        '''
        for page in self.get_pupatype_view(pupatype):
            yield from page

    # Generators for each specific pupa type.
    def gen_events(self):
        yield from self.yield_pupatype_objects('events')

    def gen_bills(self):
        yield from self.yield_pupatype_objects('bills')

    def gen_people(self):
        yield from self.yield_pupatype_objects('people')

    def gen_orgs(self):
        yield from self.yield_pupatype_objects('orgs')


class FormMixin:
    '''Handles posting data to a form and paging through the results.
    '''
    skip_first_submit = False

    def submit(self, formdata=None):
        resp = self.cfg.client.post(self.url, formdata)
        doc = lxml.html.fromstring(resp.text)
        doc.make_links_absolute(self.url)
        self.doc = doc

    @property
    def form(self):
        '''All pages on the site conveniently seem to have only one
        form each.
        '''
        form = self.doc.forms[0]
        # Test our assumption that this is that page's main form.
        assert self.url.endswith(form.action)
        return form

    def get_query(self, **kwargs):
        raise NotImplemented()

    def get_next_page(self):
        '''Is the current view paginated?
        '''
        import pdb; pdb.set_trace()
        a = self.doc.xpath(self.cfg.PGN_NEXT_PAGE_XPATH)
        if not a:
            return

    def submit_next_page(self):
        next_page = self.get_next_page()
        event_target = next_page[0].attrib['href'].split("'")[1]
        formdata = dict(doc.forms[0].fields)
        formdata['__EVENTTARGET'] = event_target
        self.doc = self.lxmlize(formdata)

    def __iter__(self):
        if not self.skip_first_submit:
            self.submit(self.get_query())
        yield self.TableClass(self.doc, self.cfg)
        while True:
            self.submit_next_page()
            yield self.TableClass(self.doc, self.cfg)


# ----------------------------------------------------------------------------
# Results classes
# ----------------------------------------------------------------------------
class DetailVisitor(Visitor):
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


class TextRenderer(Visitor):
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


class DetailPage(View):

    @CachedAttr
    def field_data(self):
        G = visitors.ext.etree.from_html(self.doc)
        return DetailVisitor(self.cfg).visit(G)

    def asdict(self):
        raise NotImplemented()


class EventDetail(DetailPage):

    def get_when(self):
        date = self.field_data[self.cfg.EVT_DETAIL_TEXT_DATE].text
        time = self.field_data[self.cfg.EVT_DETAIL_TEXT_TIME].text
        dt = datetime.strptime(
            '%s %s' % (date, time), self.cfg.EVT_DETAIL_DATETIME_FORMAT)
        return dt

    def get_location(self):
        return self.field_data[self.cfg.EVT_DETAIL_TEXT_LOCATION].text

    def asdict(self):
        data = {}
        data['when'] = self.get_when()
        data['location'] = self.get_location()

        # Documents
        documents = data['documents'] = []
        for key in self.cfg.EVT_DETAIL_PUPA_DOCUMENTS:
            field = self.field_data.get(key)
            # This column isn't present on this legistar instance.
            if field is None:
                continue
            if field.is_blank():
                continue
            document = dict(
                name=field.text,
                url=field.url,
                mimetype=field.mimetype)
            documents.append(document)

        # Participants
        participants = data['participants'] = []
        for entity_type, keys in self.cfg.EVT_TABLE_PUPA_PARTICIPANTS.items():
            for key in keys:
                cell = self.field_data[key]
                participant = dict(name=cell.text, type=entity_type)
                participants.append(participant)

        sources = data['sources'] = []
        # sources.append(dict(url=self.form_url))

        form = EventDetailForm(self.cfg, doc=self.doc)
        for x in form:
            import pdb; pdb.set_trace()
        # sources.append(dict(url=self.get_detail_url()))
        # sources.append(dict(url=self.get_ical_url()))

        return data


class NoRecordsFound(Exception):
    '''Raised if query returns no records.
    '''


class TableRow(OrderedDict):
    '''Provides access to table rows.
    '''
    def __init__(self, *args, config=None, **kwargs):
        if config is None:
            raise Exception('Pass in the config object please.')
        self.config = self.cfg = config
        super().__init__(*args, **kwargs)

    @CachedAttr
    def detail_page(self):
        return self.DetailClass(self.cfg, url=self.get_detail_url())


class TableCell:
    '''Provides access to table cells.
    '''
    def __init__(self, td, config_obj):
        self.td = td
        self.config_obj = self.cfg = config_obj

    @property
    def url(self):
        return self.td.xpath('string(.//a/@href)')

    @property
    def text(self):
        buf = io.StringIO()
        first = True
        for chunk in self.td.itertext():
            chunk = chunk.strip()
            if not chunk:
                continue
            if not first:
                buf.write(' ')
            buf.write(chunk)
            first = False
        return buf.getvalue()

    def is_blank(self):
        if self.text.strip().replace('\xa0', ' ') == 'Not available':
            return True

    @property
    def mimetype(self):
        gif_url = self.td.xpath('string(.//img/@src)')
        path = urlparse(gif_url).path
        if gif_url is None:
            return
        mimetypes = {
            self.cfg.MIMETYPE_GIF_PDF: 'application/pdf',
        }
        mimetype = mimetypes[path]
        return mimetype


class Table(View):
    '''Provides access to row data in tabular search results data.
    '''
    RowClass = TableRow
    CellClass = TableCell

    def __init__(self, doc, cfg):
        self.doc = doc
        self.cfg = cfg

    @property
    def table_element(self):
        els = self.doc.xpath(self.cfg.RESULTS_TABLE_XPATH)
        assert len(els) == 1
        return els.pop()

    def _gen_header_text(self):
        for th in self.table_element.xpath('.//th'):
            # Remove nonbreaking spaces.
            text = th.text_content().replace('\xa0', ' ')
            yield text.strip()

    def get_header_text(self):
        return tuple(self._gen_header_text())

    def gen_rows(self):
        '''Yield table row objects.
        '''
        header_text = self.get_header_text()
        for tr in self.doc.xpath('//tr[contains(@class, "rgRow")]'):

            # Complain if no records.
            if self.cfg.NO_RECORDS_FOUND_TEXT in tr.text_content():
                raise NoRecordsFound()

            tds = []
            for el in tr.xpath('.//td'):
                tds.append(self.CellClass(el, self.cfg))

            # Complain if number of cells isn't right.
            assert len(tds) == len(header_text)

            # Create a super wrappy set of wrapped wrappers.
            record = self.RowClass(zip(header_text, tds), config=self.cfg)
            yield record

    def __iter__(self):
        yield from self.gen_rows()


class CalendarTableRow(TableRow):
    DetailClass = EventDetail

    def get_name(self):
        return self[self.cfg.EVT_TABLE_TEXT_TOPIC].text

    def get_when(self):
        date = self[self.cfg.EVT_TABLE_TEXT_DATE].text
        time = self[self.cfg.EVT_TABLE_TEXT_TIME].text
        dt = datetime.strptime(
            '%s %s' % (date, time), self.cfg.EVT_TABLE_DATETIME_FORMAT)
        return dt

    def get_end(self):
        end_time = re.search(r'DTEND:([\dT]+)', self.ical_data).group(1)
        dt = datetime.strptime(end_time, r'%Y%m%dT%H%M%S')
        return dt

    def get_location(self):
        return self[self.cfg.EVT_TABLE_TEXT_LOCATION].text

    @CachedAttr
    def ical_data(self):
        print('getting ical data')
        ical_url = self.get_ical_url()
        resp = self.cfg.client.session.get(ical_url)
        return resp.text

    def get_detail_url(self):
        return self[self.cfg.EVT_TABLE_TEXT_DETAILS].url

    def get_ical_url(self):
        return self[self.cfg.EVT_TABLE_TEXT_ICAL].url

    def asdict(self):
        data = {}
        data['name'] = self.get_name()
        data['when'] = self.get_when()
        data['end'] = self.get_end()
        data['location'] = self.get_location()

        # Documents
        documents = data['documents'] = []
        for key in self.cfg.EVT_TABLE_PUPA_DOCUMENTS:
            cell = self.get(key)
            # This column isn't present on this legistar instance.
            if cell is None:
                continue
            if cell.is_blank():
                continue
            document = dict(
                name=cell.text,
                url=cell.url,
                mimetype=cell.mimetype)
            documents.append(document)

        # Participants
        participants = data['participants'] = []
        for entity_type, keys in self.cfg.EVT_TABLE_PUPA_PARTICIPANTS.items():
            for key in keys:
                cell = self[key]
                participant = dict(name=cell.text, type=entity_type)
                participants.append(participant)

        sources = data['sources'] = []
        # sources.append(dict(url=self.form_url))
        sources.append(dict(url=self.get_detail_url()))
        sources.append(dict(url=self.get_ical_url()))

        return data


class EventDetailForm(View, FormMixin):
    skip_first_submit = True
    TableClass = Table


class CalendarTable(Table):
    RowClass = CalendarTableRow


class Calendar(View, FormMixin):
    TableClass = CalendarTable

    def get_query(self, time_period=None, bodies=None):
        time_period = time_period or self.cfg.EVENTS_DEFAULT_TIME_PERIOD
        bodies = bodies or self.cfg.EVENTS_DEFAULT_BODIES
        query = {
            self.cfg.EVENTS_BODIES_EL_NAME: bodies,
            self.cfg.EVENTS_TIME_PERIOD_EL_NAME: time_period,
            }
        return query


class Legislation(View):

    def is_advanced(self):
        return self.BILLS_SIMPLE_SEARCH_TEXT in self.text

    def is_simple(self):
        return self.BILLS_ADVANCED_SEARCH_TEXT in self.text


# ----------------------------------------------------------------------------
# Overridable config data
# ----------------------------------------------------------------------------

PUPATYPES = ('events', 'orgs', 'people', 'bills')
PUPATYPE_PREFIXES = [s.upper() for s in PUPATYPES]


class TabMeta:

    def __get__(self, inst, type_=None):
        self.inst = inst
        return self

    def _gen_tabs(self):
        for pupatype in PUPATYPE_PREFIXES:
            yield getattr(self.inst, pupatype + '_TAB_META')

    @property
    def by_pupatype(self):
        return {tab.pupatype: tab for tab in self._gen_tabs()}

    @property
    def by_text(self):
        return {tab.text: tab for tab in self._gen_tabs()}


class FormsMeta:

    def __get__(self, inst, type_=None):
        self.inst = inst
        return self

    def _gen_form_types(self):
        for pupatype in PUPATYPE_PREFIXES:
            yield getattr(self.inst, pupatype + '_FORM_CLASS')

    def _gen_table_types(self):
        for pupatype in PUPATYPE_PREFIXES:
            yield getattr(self.inst, pupatype + '_TABLE_CLASS')

    FormMeta = namedtuple('FormMeta', 'pupatype, formtype, tabletype')

    def _gen_meta(self):
        form_types = self._gen_form_types()
        table_types = self._gen_table_types()
        for meta in zip(PUPATYPES, form_types, table_types):
            yield self.FormMeta._make(meta)

    @property
    def by_pupatype(self):
        return {meta.pupatype: meta for meta in self._gen_meta()}

    @property
    def by_text(self):
        return {meta.text: meta for meta in self._gen_meta()}


class Config:

    SESSION_CLASS = requests.Session

    # Preceding slashes are necessary
    MIMETYPE_GIF_PDF = '/Images/PDF.gif'

    TAB_TEXT_ID = 'ctl00_tabTop'
    TAB_TEXT_XPATH_TMPL = 'string(//div[@id="%s"]//a[contains(@class, "rtsSelected")])'
    TAB_TEXT_XPATH = TAB_TEXT_XPATH_TMPL % TAB_TEXT_ID

    # These are config options that can be overridden.
    tabs = TabMeta()
    TabItemMeta = namedtuple('TabMeta', 'path, text, pupatype')
    EVENTS_TAB_META = TabItemMeta('Calendar.aspx', 'Calendar', 'events')
    ORGS_TAB_META = TabItemMeta('Departments.aspx', 'Committees', 'orgs')
    BILLS_TAB_META = TabItemMeta('Legislation.aspx', 'Legislation', 'bills')
    PEOPLE_TAB_META = TabItemMeta('MainBody.aspx', 'City Council', 'people')

    # Url paths.
    EVENT_DETAIL_PATH = 'MeetingDetail.aspx'
    ORG_DETAIL_PATH = 'DepartmentDetail.aspx'

    # Pagination.
    PGN_CURRENT_PAGE_TMPL = '//*[contains(@class, "%s")]'
    PGN_CURRENT_PAGE_CLASS = 'rgCurrentPage'
    PGN_CURRENT_PAGE_XPATH = PGN_CURRENT_PAGE_TMPL % PGN_CURRENT_PAGE_CLASS
    PGN_NEXT_PAGE_TMPL = '%s/following-sibling::a[1]'
    PGN_NEXT_PAGE_XPATH = '%s/following-sibling::a[1]' % PGN_CURRENT_PAGE_XPATH

    forms = FormsMeta()
    EVENTS_FORM_CLASS = Calendar
    EVENTS_TABLE_CLASS = Calendar
    BILLS_FORM_CLASS = Legislation
    BILLS_TABLE_CLASS = Table
    PEOPLE_FORM_CLASS = Legislation
    PEOPLE_TABLE_CLASS = Table
    ORGS_FORM_CLASS = Legislation
    ORGS_TABLE_CLASS = Table

    NO_RECORDS_FOUND_TEXT = 'No records were found'
    RESULTS_TABLE_XPATH = '//table[contains(@class, "rgMaster")]'

    # ------------------------------------------------------------------------
    # Events config
    # ------------------------------------------------------------------------
    EVENTS_DEFAULT_TIME_PERIOD = 'This Year'
    EVENTS_DEFAULT_BODIES = 'All Committees'
    EVENTS_BODIES_EL_NAME = 'ctl00$ContentPlaceHolder1$lstBodies'
    EVENTS_TIME_PERIOD_EL_NAME = 'ctl00$ContentPlaceHolder1$lstYears'

    # ------------------------------------------------------------------------
    # Events table config.
    EVT_TABLE_TEXT_NAME = 'Name'
    EVT_TABLE_TEXT_DATE =  'Meeting Date'
    EVT_TABLE_TEXT_ICAL =  ''
    EVT_TABLE_TEXT_TIME = 'Meeting Time'
    EVT_TABLE_TEXT_LOCATION = 'Meeting Location'
    EVT_TABLE_TEXT_TOPIC = 'Meeting Topic'
    EVT_TABLE_TEXT_DETAILS = 'Meeting Details'
    EVT_TABLE_TEXT_AGENDA = 'Agenda'
    EVT_TABLE_TEXT_MINUTES = 'Minutes'
    EVT_TABLE_TEXT_MEDIA = 'Multimedia'
    EVT_TABLE_TEXT_NOTICE = 'Notice'

    EVT_TABLE_DATETIME_FORMAT = '%m/%d/%Y %I:%M %p'

    EVT_TABLE_PUPA_KEY_NAME = EVT_TABLE_TEXT_TOPIC
    EVT_TABLE_PUPA_KEY_LOCATION = EVT_TABLE_TEXT_LOCATION

    EVT_TABLE_PUPA_PARTICIPANTS = {
        'organization': [EVT_TABLE_TEXT_NAME]
        }

    EVT_TABLE_PUPA_DOCUMENTS = [
        EVT_TABLE_TEXT_AGENDA,
        EVT_TABLE_TEXT_MINUTES,
        EVT_TABLE_TEXT_NOTICE,
        ]

    # ------------------------------------------------------------------------
    # Events detail config.
    EVT_DETAIL_TEXT_NAME = EVT_TABLE_TEXT_NAME
    EVT_DETAIL_TEXT_TOPIC = EVT_TABLE_TEXT_TOPIC
    EVT_DETAIL_TEXT_DETAILS = EVT_TABLE_TEXT_DETAILS
    EVT_DETAIL_TEXT_MEDIA = EVT_TABLE_TEXT_MEDIA
    EVT_DETAIL_TEXT_NOTICE = EVT_TABLE_TEXT_NOTICE
    EVT_DETAIL_TEXT_LOCATION = 'Meeting location'
    EVT_DETAIL_TEXT_DATE = 'Date'
    EVT_DETAIL_TEXT_TIME = 'Time'
    EVT_DETAIL_TEXT_VIDEO = 'Meeting video'
    EVT_DETAIL_TEXT_AGENDA = 'Published agenda'
    EVT_DETAIL_TEXT_AGENDA_STATUS = 'Agenda status'
    EVT_DETAIL_TEXT_MINUTES = 'Published minutes'
    EVT_DETAIL_TEXT_MINUTES_STATUS = 'Minutes status'
    EVT_DETAIL_TEXT_SUMMARY = 'Published summary'

    EVT_DETAIL_DATETIME_FORMAT = EVT_TABLE_DATETIME_FORMAT

    EVT_DETAIL_PUPA_KEY_NAME = EVT_DETAIL_TEXT_TOPIC
    EVT_DETAIL_PUPA_KEY_LOCATION = EVT_DETAIL_TEXT_LOCATION

    EVT_DETAIL_PUPA_PARTICIPANTS = {
        'organization': [EVT_DETAIL_TEXT_NAME]
        }

    EVT_DETAIL_PUPA_DOCUMENTS = [
        EVT_DETAIL_TEXT_AGENDA,
        EVT_DETAIL_TEXT_MINUTES,
        EVT_DETAIL_TEXT_NOTICE,
        EVT_DETAIL_TEXT_VIDEO,
        ]

    # ------------------------------------------------------------------------
    # Bill search config.
    BILLS_SIMPLE_SEARCH_TEXT = '<<< Simple Search'
    BILLS_ADVANCED_SEARCH_TEXT = 'Detailed Search >>>'

    @CachedAttr
    def client(self):
        return Client(self)


# ----------------------------------------------------------------------------
# Implementations
# ----------------------------------------------------------------------------
class Nyc(Config):
    root_url = 'http://legistar.council.nyc.gov/'

    # Requests args.
    proxies = dict.fromkeys(['http', 'https'], 'http://localhost:8080')
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.6) '
            'Gecko/20070725 Firefox/2.0.0.6')
        }
    requests_kwargs = dict(
        proxies=proxies,
        headers=headers)



if __name__ == '__main__':
    import pprint
    site = Root(Nyc)
    print(site.get_active_tab())
    for obj in site.gen_events():
        pprint.pprint(obj.asdict())
        deets = obj.detail_page.asdict()
        import pdb; pdb.set_trace()
