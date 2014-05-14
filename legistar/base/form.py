import lxml.html
from legistar.base.ctx import CtxMixin


class Form(CtxMixin):
    '''Handles posting data to a form and paging through the results.
    '''
    skip_first_submit = False

    def __init__(self, view):
        self.view = self.inherit_ctx_from(view)

    def submit(self, formdata=None):
        resp = self.cfg.client.post(self.url, formdata)
        doc = lxml.html.fromstring(resp.text)
        doc.make_links_absolute(self.url)
        self.doc = doc

    def get_query(self, **kwargs):
        '''This function returns the dictionary of POST data
        the form requires.
        '''
        raise NotImplementedError()

    def get_next_page(self):
        '''Is the current view paginated?
        '''
        if 'search' in self.__class__.__qualname__.lower():
            import pdb; pdb.set_trace()
        a = self.doc.xpath(self.cfg.PGN_NEXT_PAGE_XPATH)
        if not a:
            return

    def submit_next_page(self):
        next_page = self.get_next_page()
        # event_target = next_page[0].attrib['href'].split("'")[1]
        # formdata = dict(doc.forms[0].fields)
        # formdata['__EVENTTARGET'] = event_target
        # self.doc = self.lxmlize(formdata)

    def __iter__(self):
        Table = self.view.viewtype_meta.Table
        if not self.skip_first_submit:
            self.submit(self.get_query())
        table = self.make_child(Table, view=self.view)
        yield from table
        while True:
            if not self.submit_next_page():
                break
            table = self.make_child(Table, view=self.view)
            yield from table
