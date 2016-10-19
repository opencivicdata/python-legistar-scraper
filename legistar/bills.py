from .base import LegistarScraper, LegistarAPIScraper
from pupa.scrape import Scraper
from lxml.etree import tostring
from collections import deque
from functools import partialmethod
import datetime
import pytz
import requests

class LegistarBillScraper(LegistarScraper):
    def legislation(self, search_text='', created_after=None, 
                    created_before=None) :

        # If legislation is added to the the legistar system while we
        # are scraping, it will shift the list of legislation down and
        # we might revisit the same legislation. So, we keep track of
        # the last few pieces of legislation we've visited in order to
        # make sure we are not revisiting
        scraped_leg = deque([], maxlen=10)

        for page in self.searchLegislation(search_text, created_after,
                                           created_before) :
            for legislation_summary in self.parseSearchResults(page) :
                if not legislation_summary['url'] in scraped_leg :
                    yield legislation_summary
                    scraped_leg.append(legislation_summary['url'])

    def searchLegislation(self, search_text='', created_after=None,
                          created_before=None):
        """
        Submit a search query on the legislation search page, and return a list
        of summary results.
        """

        page = self.lxmlize(self.LEGISLATION_URL)

        page = self._advancedSearch(page)

        payload = {}

        # Enter the search parameters TODO: Each of the possible form
        # fields should be represented as keyword arguments to this
        # function. The default query string should be for the the
        # default 'Legislative text' field.
        payload['ctl00$ContentPlaceHolder1$txtText'] = search_text

        if created_after and created_before :
            payload.update(dateWithin(created_after, created_before))

        elif created_before :
            payload.update(dateBound(created_before))
            payload['ctl00$ContentPlaceHolder1$radFileCreated'] = '<'

        elif created_after :
            payload.update(dateBound(created_after))
            payload['ctl00$ContentPlaceHolder1$radFileCreated'] = '>'


        # Return up to one million search results
        payload['ctl00_ContentPlaceHolder1_lstMax_ClientState'] = '{"value":"1000000"}'
        payload['ctl00_ContentPlaceHolder1_lstYearsAdvanced_ClientState'] = '{"value":"All"}'
        payload['ctl00$ContentPlaceHolder1$btnSearch'] = 'Search Legislation'


        payload.update(self.sessionSecrets(page))

        return self.pages(self.LEGISLATION_URL, payload)

    def parseSearchResults(self, page) :
        """Take a page of search results and return a sequence of data
        of tuples about the legislation, of the form

        ('Document ID', 'Document URL', 'Type', 'Status', 'Introduction Date'
        'Passed Date', 'Main Sponsor', 'Title')
        """
        table = page.xpath("//table[@id='ctl00_ContentPlaceHolder1_gridMain_ctl00']")[0]
        for legislation, headers, row in self.parseDataTable(table):
            # Do legislation search-specific stuff
            # ------------------------------------
            # First column should be the ID of the record.
            id_key = headers[0]
            try:
                legislation_id = legislation[id_key]['label']
            except TypeError:
                continue
            legislation_url = legislation[id_key]['url'].split(self.BASE_URL)[-1]
            legislation[id_key] = legislation_id
            legislation['url'] = self.BASE_URL + legislation_url.split('&Options')[0] + '&FullText=1'

            yield legislation

    def _advancedSearch(self, page) :
        search_switcher = page.xpath("//input[@id='ctl00_ContentPlaceHolder1_btnSwitch']")[0]

        if 'simple search' in search_switcher.value.lower() :
            return page
        else :
            payload = self.sessionSecrets(page)
            payload[search_switcher.name] = search_switcher.value

            page = self.lxmlize(self.LEGISLATION_URL, payload)

            if 'simple search' not in page.xpath("//input[@id='ctl00_ContentPlaceHolder1_btnSwitch']")[0].value.lower() :
                raise ValueError('Not on the advanced search page')

            return page

    def details(self, detail_url, div_id) :
        detail_page = self.lxmlize(detail_url)
        
        detail_div = detail_page.xpath(".//div[@id='%s']" % div_id)[0]

        return self.parseDetails(detail_div)

    def legDetails(self, detail_url) :
        div_id = 'ctl00_ContentPlaceHolder1_pageDetails'
        return self.details(detail_url, div_id)

    def actionDetails(self, detail_url) :
        div_id = 'ctl00_ContentPlaceHolder1_pageTop1'
        return self.details(detail_url, div_id)

    def history(self, detail_url) :
        detail_page = self.lxmlize(detail_url)

        try :
            history_table = detail_page.xpath("//table[@id='ctl00_ContentPlaceHolder1_gridLegislation_ctl00']")[0]
        except IndexError :
            print(detail_url)
            raise

        history = [row[0] for row in self.parseDataTable(history_table)] 

        try :
            history = sorted(history, key = self._actionSortKey)
        except (TypeError, ValueError) :
            pass

        for action in history :
            yield action

                    
    def _actionSortKey(self, action) :
        action_date = self.toDate(action['Date'])
        action_url = action['Action\xa0Details']['url']

        return (action_date, action_url)

    def text(self, detail_url) :
        detail_page = self.lxmlize(detail_url)

        text_div = detail_page.xpath("//div[@id='ctl00_ContentPlaceHolder1_divText']")

        if len(text_div) :
            return tostring(text_div[0], pretty_print=True).decode()
        else :
            return None

        
        

    def extractVotes(self, action_detail_url) :
        action_detail_page = self.lxmlize(action_detail_url)
        try:
            vote_table = action_detail_page.xpath("//table[@id='ctl00_ContentPlaceHolder1_gridVote_ctl00']")[0]
        except IndexError:
            self.warning("No votes found in table")
            return None, []
        votes = list(self.parseDataTable(vote_table))
        vote_list = []
        for vote, _, _ in votes :
            raw_option = vote['Vote'].lower()
            vote_list.append((self.VOTE_OPTIONS.get(raw_option, raw_option), 
                              vote['Person Name']['label']))

        action_detail_div = action_detail_page.xpath(".//div[@id='ctl00_ContentPlaceHolder1_pageTop1']")[0]
        action_details = self.parseDetails(action_detail_div)
        result = action_details['Result'].lower()

        return result, vote_list
        

def dateWithin(created_after, created_before) :
    payload = dateBound(created_after)

    payload['ctl00$ContentPlaceHolder1$txtFileCreated2'] =\
        '{d.year}-{d.month:02}-{d.day:02}'.format(d=created_before)
    payload['ctl00$ContentPlaceHolder1$txtFileCreated2$dateInput'] =\
        '{d.month}/{d.day}/{d.year}'.format(d=created_before)

    payload['ctl00_ContentPlaceHolder1_txtFileCreated2_dateInput_ClientState'] =\
        '{{"enabled":true, "emptyMessage":"","validationText":"{d.year}-{d.month:02}-{d.day:02}-00-00-00","valueAsString":"{d.year}-{d.month:02}-{d.day:02}-00-00-00","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00", "lastSetTextBoxValue":"{d.month}/{d.day}/{d.year}"}}'.format(d=created_before)

    payload['ctl00$ContentPlaceHolder1$radFileCreated'] = 'between'

    return payload

def dateBound(creation_date) :
    payload = {}

    payload['ctl00$ContentPlaceHolder1$txtFileCreated1'] =\
        '{d.year}-{d.month:02}-{d.day:02}'.format(d=creation_date)
    payload['ctl00$ContentPlaceHolder1$txtFileCreated1$dateInput'] =\
        '{d.month}/{d.day}/{d.year}'.format(d=creation_date)

    payload['ctl00_ContentPlaceHolder1_txtFileCreated1_dateInput_ClientState'] =\
        '{{"enabled":true, "emptyMessage":"","validationText":"{d.year}-{d.month:02}-{d.day:02}-00-00-00","valueAsString":"{d.year}-{d.month:02}-{d.day:02}-00-00-00","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00", "lastSetTextBoxValue":"{d.month}/{d.day}/{d.year}"}}'.format(d=creation_date)

    return payload

class LegistarAPIBillScraper(LegistarAPIScraper) :

    def matters(self, since_date) :
        since_date = datetime.datetime.strftime(since_date, '%Y-%m-%d')
        params = {'$filter' : "MatterLastModifiedUtc gt datetime'{since_date}'".format(since_date = since_date)}
        
        matters_url = self.BASE_URL + '/matters'
        seen_matters = deque([], maxlen=1000)

        page_num = 0
        while page_num == 0 or len(response.json()) == 1000 :
            params['$skip'] = page_num * 1000
            response = self.get(matters_url, params=params)

            for matter in response.json() :
                if matter["MatterId"] not in seen_matters :
                    yield matter
                    seen_matters.append(matter["MatterId"])

            page_num += 1

    def endpoint(self, route, *args) :
        url = self.BASE_URL + route
        response = self.get(url.format(*args))
        return response.json()

    topics = partialmethod(endpoint, '/matters/{0}/indexes')
    attachments = partialmethod(endpoint, '/matters/{0}/attachments')
    code_sections = partialmethod(endpoint, 'matters/{0}/codesections')

    def votes(self, history_id) :
        url = self.BASE_URL + '/eventitems/{0}/votes'.format(history_id)
        response = requests.get(url)
        if response.status_code == 200 :
            return response.json()
        elif response.status_code == 500 and response.json().get('InnerException', {}).get('ExceptionMessage', '') == "The cast to value type 'System.Int32' failed because the materialized value is null. Either the result type's generic parameter or the query must use a nullable type." :
            return []
        else :
            response = self.get(url)
            return response.json()

    def history(self, matter_id) :
        actions = self.endpoint('/matters/{0}/histories', matter_id)
        try:
            return sorted(actions, 
                          key = lambda action : action['MatterHistoryActionDate'])
        except TypeError:
            return actions

    def sponsors(self, matter_id) :
        spons = self.endpoint('/matters/{0}/sponsors', matter_id)
        max_version = str(max(int(sponsor['MatterSponsorMatterVersion'])
                              for sponsor in spons))
        spons = [sponsor for sponsor in spons
                 if sponsor['MatterSponsorMatterVersion'] == max_version]
        return sorted(spons, 
                      key = lambda sponsor : sponsor["MatterSponsorSequence"])

    def text(self, matter_id) :
        version_route = '/matters/{0}/versions'
        text_route = '/matters/{0}/texts/{1}'

        versions = self.endpoint(version_route, matter_id)
        
        latest_version = max(versions, key=lambda x : x['Value'])['Key']
        
        text_url = self.BASE_URL + text_route.format(matter_id, latest_version)
        response = self.get(text_url, stream=True)
        if int(response.headers['Content-Length']) < 21052630 :
            return response.json()

    def legislation_detail_url(self, matter_id) :
        gateway_url = self.BASE_WEB_URL + '/gateway.aspx?m=l&id=/matter.aspx?key={0}'
        
        legislation_detail_route = self.head(gateway_url.format(matter_id)).headers['Location']
        
        return self.BASE_WEB_URL + legislation_detail_route

