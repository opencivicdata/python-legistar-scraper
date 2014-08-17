import re
import itertools

import lxml.html
from selenium.common.exceptions import NoSuchElementException

from legistar.base import Base


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

    def before_first_submit(self):
        '''This function runs before the first submit.
        '''
        pass

    def submit(self, formdata=None, extra_headers=None):
        # Call the pre-submit hook.
        if not self._submitted_first:
            self.before_first_submit()
            self._submitted_first = True

        # Then submit the form.
        self.debug('%r is fetching %s', self, self.url)
        resp = self.cfg.client.post(self.url, formdata, extra_headers)
        doc = lxml.html.fromstring(resp.text)
        doc.make_links_absolute(self.url)
        self.doc = doc

    def get_query(self, **kwargs):
        '''This function returns the dictionary of POST data
        the form requires.
        '''
        raise NotImplementedError()

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
        get_query = getattr(self, 'get_pagination_query', self.get_query)

        # Include the pagination target thingy in the query this time.
        formdata = get_query(__EVENTTARGET=event_target)

        # Blab.
        msg = '%r requesting page %d of search results: %r'
        formdata_copy = dict(formdata)
        formdata_copy.pop('__VIEWSTATE', None)
        formdata_copy.pop('__EVENTVALIDATION', None)
        self.info(msg, self, next(self.count), formdata_copy)

        # Re-submit the form.
        extra_headers = dict(referer=self.url)
        self.submit(formdata, extra_headers)

    def __iter__(self):
        yield from self.gen_documents()

    def gen_documents(self):
        Table = self.view.viewtype_meta.Table
        if self.skip_first_submit:
            pass
        else:
            self.submit(self.get_query())
        yield from self.make_child(Table, view=self.view)
        while True:
            self.submit_next_page()
            yield from self.make_child(Table, view=self.view)


class FirefoxForm(Form):

    def gen_docs_from_lxmldoc(self):
        Table = self.view.viewtype_meta.Table
        doc = self.lxmlize()
        doc.make_links_absolute(self.url)
        self.doc = doc
        table = self.make_child(Table, view=self.view)
        yield from table

    def lxmlize(self):
        html = self.firefox.page_source
        doc = lxml.html.fromstring(html)
        return doc

    def set_dropdown(self, id, text):
        script = '''
            $find('{id}').findItemByText('{val}').select();
        '''.format(id=id, val=text)
        self.firefox.execute_script(script.strip())

    def fill_out_form(self):
        pass

    def gen_documents(self):
        self.firefox.get(self.url)

        self.fill_out_form()

        submit_name = self.get_config_value('submit_button_name')
        button = self.firefox.find_element_by_name(submit_name)
        button.click()

        # Yield docs on the first page.
        yield from self.gen_docs_from_lxmldoc()

        # Then subsequent pages.
        while True:
            xpath = '//*[@class="rgCurrentPage"]/following-sibling::a'
            try:
                next_page = self.firefox.find_element_by_xpath(xpath)
            except NoSuchElementException:
                return
            next_page.click()
            yield from self.gen_docs_from_lxmldoc()
