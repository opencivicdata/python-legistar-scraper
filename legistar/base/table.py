from collections import OrderedDict

from hercules import CachedAttr


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


class Table:
    '''Provides access to row data in tabular search results data.
    '''
    RowClass = TableRow
    CellClass = TableCell

    def __init__(self, view):
        self.view = view

    @property
    def doc(self):
        return self.view.doc

    @property
    def config_obj(self):
        return self.view.config_obj

    cfg = config_obj

    @property
    def row_class(self):
        return self.cfg.viewmeta

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
