import io
from urllib.parse import urlparse
from collections import defaultdict

from legistar.base import Base
from legistar.fields import FieldAggregator


class TableRow(FieldAggregator):
    '''Provides access to table rows.
    '''
    def __init__(self, data, view, **kwargs):
        self.view = view
        self.field_data = defaultdict(list)
        for key, field in data:
            self.field_data[key].append(field)

    def get_detail_viewtype(self):
        return self.view.viewmeta.detail.View

    def get_detail_page(self):
        DetailView = self.get_detail_viewtype()
        detail_view = DetailView(url=self.get_detail_url())
        detail_view.inherit_chainmap_from(self.view)
        return detail_view


class Table(Base):
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
        for th in self.table_element.xpath('.//th[contains(@class, "rgHeader")]'):
            # Remove nonbreaking spaces.
            text = th.text_content().replace('\xa0', ' ')
            yield text.strip()

    def get_header_text(self):
        return tuple(self._gen_header_text())

    def get_table_cell_type(self):
        return self.view.viewtype_meta.TableCell

    def get_table_row_type(self):
        return self.view.viewtype_meta.TableRow

    def gen_rows(self):
        '''Yield table row objects.
        '''
        TableCell = self.get_table_cell_type()
        TableRow = self.get_table_row_type()
        header_text = self.get_header_text()

        for tr in self.table_element.xpath('.//tr')[1:]:

            # Skip the pagination rows.
            class_attr = tr.attrib.get('class', '')
            if 'rgPager' in class_attr:
                continue

            # Skip filter rows.
            if 'rgFilterRow' in class_attr:
                continue

            if tr.xpath('.//td[contains(@class, "rgPagerCell")]'):
                continue

            # Skip weird col rows.
            if tr.xpath('.//th[@scope="col"]'):
                continue

            # Complain if no records.
            for no_records_text in self.cfg.NO_RECORDS_FOUND_TEXT:
                if no_records_text in tr.text_content().strip():
                    msg = 'No records found in %r. Moving on.'
                    self.debug(msg % self)
                    raise StopIteration()

            for bad_query_text in self.cfg.BAD_QUERY_TEXT:
                if bad_query_text in tr.text_content().strip():
                    msg = ('Invalid query! This means the function that '
                           'determines the query data probably needs edits.')
                    self.critical(msg)
                    raise StopIteration()

            # Collect all the cells.
            cells = []
            for el in tr.xpath('.//td'):
                cell = self.make_child(TableCell, el)
                cells.append(cell)

            # Complain if number of cells doesn't align with the headers.
            assert len(cells) == len(header_text)

            # Create a super wrappy set of wrapped wrappers.
            data = zip(header_text, cells)
            document = self.make_child(TableRow, data, view=self.view)
            try:
                yield document.asdict()
            except self.SkipDocument:
                pass


    def __iter__(self):
        yield from self.gen_rows()
