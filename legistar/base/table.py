import io
from urllib.parse import urlparse
from collections import OrderedDict

from hercules import CachedAttr

from legistar.base.field import FieldAggregator, FieldAccessor
from legistar.base.ctx import CtxMixin


class NoRecordsFound(Exception):
    '''Raised if query returns no records.
    '''


class TableRow(FieldAggregator):
    '''Provides access to table rows.
    '''
    def __init__(self, *args, view, **kwargs):
        self.view = view
        self.field_data = OrderedDict(*args, **kwargs)

    @CachedAttr
    def detail_page(self):
        DetailView = self.view.viewmeta.detail.View
        detail_view = DetailView(url=self.get_detail_url())
        detail_view.inherit_ctx_from(self.view)
        return detail_view


class TableCell(FieldAccessor):
    '''Provides access to table cells.
    '''
    def __init__(self, td):
        self.td = td

    def get_url(self):
        return self.td.xpath('string(.//a/@href)')

    def get_text(self):
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

    def get_mimetype(self):
        gif_url = self.td.xpath('string(.//img/@src)')
        path = urlparse(gif_url).path
        if gif_url is None:
            return
        mimetypes = {
            self.cfg.MIMETYPE_GIF_PDF: 'application/pdf',
        }
        mimetype = mimetypes[path]
        return mimetype


class Table(CtxMixin):
    '''Provides access to row data in tabular search results data.
    Tables inherit the context of the view's form. So self.doc on a table
    is really self.doc on the form.
    '''
    def __init__(self, view):
        self.view = view

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
        TableCell = self.view.viewtype_meta.TableCell
        TableRow = self.view.viewtype_meta.TableRow
        header_text = self.get_header_text()

        for tr in self.table_element.xpath('.//tr')[1:]:

            # Complain if no records.
            if self.cfg.NO_RECORDS_FOUND_TEXT in tr.text_content():
                raise NoRecordsFound()

            cells = []
            for el in tr.xpath('.//td'):
                cell = self.make_child(TableCell, el)
                cells.append(cell)

            # Complain if number of cells doesn't align with the headers.
            assert len(cells) == len(header_text)

            # Create a super wrappy set of wrapped wrappers.
            data = zip(header_text, cells)
            record = self.make_child(TableRow, data, view=self.view)
            yield record

    def __iter__(self):
        yield from self.gen_rows()
