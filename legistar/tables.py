import io
from urllib.parse import urlparse
from collections import OrderedDict

from legistar.base import Base, CachedAttr
from legistar.fields import FieldAggregator, FieldAccessor


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
        detail_view.inherit_chainmap_from(self.view)
        return detail_view

    def asdict(self):
        return dict(self)


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

    def gen_rows(self):
        '''Yield table row objects.
        '''
        TableCell = self.view.viewtype_meta.TableCell
        TableRow = self.view.viewtype_meta.TableRow
        header_text = self.get_header_text()

        for tr in self.table_element.xpath('.//tr')[1:]:

            # Skip the pagination rows.
            if 'rgPager' in tr.attrib.get('class', ''):
                continue

            if tr.xpath('.//td[contains(@class, "rgPagerCell")]'):
                continue

            # Skip weird col rows.
            if tr.xpath('.//th[@scope="col"]'):
                continue

            # Complain if no records.
            if tr.text_content().strip() in self.cfg.NO_RECORDS_FOUND_TEXT:
                msg = 'No records found in %r. Moving on.'
                self.debug(msg % self)
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
            record = self.make_child(TableRow, data, view=self.view)
            yield record.asdict()

    def __iter__(self):
        yield from self.gen_rows()
