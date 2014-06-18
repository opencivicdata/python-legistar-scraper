import re
import itertools

import lxml.html

from legistar.base import Base
from legistar.jurisdictions.utils import try_jxn_delegation


class Form(Base):
    '''Handles posting data to a form and paging through the results.
    '''
    skip_first_submit = False

    def __init__(self, view):
        self.view = self.inherit_chainmap_from(view)
        # We need to seed the client with the ASP viewstate nonsense
        # before trying to post to the form. This does that:
        doc = self.doc
        self.count = itertools.count(2)
        self._submitted_first = False

    @property
    def formdata(self):
        return dict(self.doc.forms[0].fields)

    @try_jxn_delegation
    def before_first_submit(self):
        '''This function runs before the first submit.
        '''
        pass

    @try_jxn_delegation
    def submit(self, formdata=None):
        # Call the pre-submit hook.
        if not self._submitted_first:
            self.before_first_submit()
            self._submitted_first = True

        # Then submit the form.
        self.debug('%r is fetching %s', self, self.url)
        resp = self.cfg.client.post(self.url, formdata)
        doc = lxml.html.fromstring(resp.text)
        doc.make_links_absolute(self.url)
        self.doc = doc

    def get_query(self, **kwargs):
        '''This function returns the dictionary of POST data
        the form requires.
        '''
        raise NotImplementedError()

    @try_jxn_delegation
    def submit_next_page(self):
        '''Submits the next page in the search results.
        '''
        js = self.doc.xpath(self.cfg.PGN_NEXT_PAGE_XPATH)
        if not js:
            # There are no more pages.
            msg = 'No more pages of search results.'
            self.info(msg)
            raise StopIteration()

        # Parse the pagination control id name thingy.
        event_target = js.split("'")[1]
        formdata = dict(__EVENTTARGET=event_target)

        # Re-submit the form.
        msg = '%r requesting page %d of search results: %r'
        self.info(msg, self, next(self.count), formdata)
        self.submit(formdata)

    @try_jxn_delegation
    def __iter__(self):
        Table = self.view.viewtype_meta.Table

        # Don't submit queries if we're testing.
        if self.skip_first_submit:
            pass
        else:
            self.submit(self.get_query())
        yield from self.make_child(Table, view=self.view)

        while True:
            self.submit_next_page()
            yield from self.make_child(Table, view=self.view)
