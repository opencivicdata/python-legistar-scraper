import lxml.html


class Form:
    '''Handles posting data to a form and paging through the results.
    '''
    skip_first_submit = False

    def __init__(self, view):
        self.view = view

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
        # event_target = next_page[0].attrib['href'].split("'")[1]
        # formdata = dict(doc.forms[0].fields)
        # formdata['__EVENTTARGET'] = event_target
        # self.doc = self.lxmlize(formdata)

    def __iter__(self):
        if not self.skip_first_submit:
            self.submit(self.get_query())
        yield self.TableClass(self.doc, self.cfg)
        while True:
            self.submit_next_page()
            yield self.TableClass(self.doc, self.cfg)
