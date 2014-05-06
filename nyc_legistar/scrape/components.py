import logging

import requests
import lxml.html
from pyvirtualdisplay import Display
from selenium import webdriver
from hercules import CachedAttr


class BillFieldVisitor:

    id_root = 'ctl00_ContentPlaceHolder1_'

    def __init__(self, doc):
        self.doc = doc

    def __iter__(self):
        xpath = '//span[contains(@id, "%s")]' % self.id_root
        for anchor in self.doc.xpath(xpath):
            idstr = anchor.attrib['id'].replace(self.id_root, '')
            method = getattr(self, 'visit_' + idstr, None)
            if method is None:
                method = self.generic_visit
            yield method(anchor)

    def visit_lblFile2(self, anchor):
        return 'file_no', anchor.text_content()

    def visit_lblVersion(self, anchor):
        return 'version', anchor.text_content()

    def visit_lblVersion2(self, anchor):
        return 'version2', anchor.text_content()
        import pdb; pdb.set_trace()

    # def visit_lblName(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblName2(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblType(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblType2(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblStatus(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblStatus2(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblInControlOf(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblOnAgenda(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblOnAgenda2(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblPassed(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblPassed2(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblEnactmentDate1(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblEnactmentDate2(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblEnactmentNumber1(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblEnactmentNumber2(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblTitle(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblTitle2(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblSponsors(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblSponsors2(self, anchor):
    #     import pdb; pdb.set_trace()

    # def visit_lblReport(self, anchor):
    #     import pdb; pdb.set_trace()

    def generic_visit(self, anchor):
        import pdb; pdb.set_trace()

class BillSpider:

    arguments = [
        (['--headless'], dict(
            type=bool,
            default=False,
            help='Very headless.')),
        (['--search-scope'], dict(
            type=str,
            default='This Week',
            help='Range to search.'))]

    def __iter__(self):
        yield from self.spider()

    base_url = 'http://legistar.council.nyc.gov/'
    legislation_url = 'http://legistar.council.nyc.gov/Legislation.aspx'

    def spider(self):
        self.browser.get(self.legislation_url)

        # Open the scope menu.
        xpath = '//input[contains(@name, "ctl00$ContentPlaceHolder1$lstYears")]'
        scope_menu = self.browser.find_elements_by_xpath(xpath)[0]
        scope_menu.click()

        # Click the scope choice.
        xpath = '//li[text()="%s"]' % self.args.search_scope
        li = self.browser.find_elements_by_xpath(xpath)[0]
        li.click()

        # Click search.
        xpath = '//input[contains(@value, "earch")]'
        search_button = self.browser.find_elements_by_xpath(xpath)[0]
        search_button.click()
        xpath = '//a[contains(@href, "LegislationDetail")]/@href'
        for url in self.getdoc().xpath(xpath):
            yield self.scrape_bill(url)

    def scrape_bill(self, url):
        self.browser.get(url)
        doc = self.getdoc()
        for item in BillFieldVisitor(doc):
            print(item)

    def getdoc(self):
        '''Get the current page as an lxml document.
        '''
        doc = lxml.html.fromstring(self.browser.page_source)
        doc.make_links_absolute(self.legislation_url)
        return doc

    @CachedAttr
    def browser(self):
        if self.args.headless:
            display = Display(visible=0, size=(800, 600))
            display.start()
        browser = webdriver.Firefox()
        browser.implicitly_wait(10)
        return browser



class ReportWriter:

    def __iter__(self):
        for thing in self.upstream:
            pass
