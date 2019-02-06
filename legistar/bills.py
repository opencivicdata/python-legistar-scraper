from .base import LegistarScraper, LegistarAPIScraper
from lxml.etree import tostring
from collections import deque
from functools import partialmethod
import requests
from urllib.parse import urljoin


class LegistarBillScraper(LegistarScraper):
    def legislation(self, search_text='', created_after=None,
                    created_before=None):

        # If legislation is added to the the legistar system while we
        # are scraping, it will shift the list of legislation down and
        # we might revisit the same legislation. So, we keep track of
        # the last few pieces of legislation we've visited in order to
        # make sure we are not revisiting
        scraped_leg = deque([], maxlen=10)

        for page in self.searchLegislation(search_text, created_after,
                                           created_before):
            for legislation_summary in self.parseSearchResults(page):
                if not legislation_summary['url'] in scraped_leg:
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

        if created_after and created_before:
            payload.update(dateWithin(created_after, created_before))

        elif created_before:
            payload.update(dateBound(created_before))
            payload['ctl00$ContentPlaceHolder1$radFileCreated'] = '<'

        elif created_after:
            payload.update(dateBound(created_after))
            payload['ctl00$ContentPlaceHolder1$radFileCreated'] = '>'

        # Return up to one million search results
        payload['ctl00_ContentPlaceHolder1_lstMax_ClientState'] = '{"value":"1000000"}'
        payload['ctl00_ContentPlaceHolder1_lstYearsAdvanced_ClientState'] = '{"value":"All"}'
        payload['ctl00$ContentPlaceHolder1$btnSearch'] = 'Search Legislation'

        payload.update(self.sessionSecrets(page))

        return self.pages(self.LEGISLATION_URL, payload)

    def parseSearchResults(self, page):
        """Take a page of search results and return a sequence of data
        of tuples about the legislation, of the form

        ('Document ID', 'Document URL', 'Type', 'Status', 'Introduction Date'
        'Passed Date', 'Main Sponsor', 'Title')
        """
        table = page.xpath(
            "//table[@id='ctl00_ContentPlaceHolder1_gridMain_ctl00']")[0]
        for legislation, headers, row in self.parseDataTable(table):
            # Do legislation search-specific stuff
            # ------------------------------------
            # First column should be the ID of the record.
            id_key = headers[0]
            try:
                legislation_id = legislation[id_key]['label']
            except TypeError:
                continue
            legislation_url = legislation[id_key]['url'].split(
                self.BASE_URL)[-1]
            legislation[id_key] = legislation_id
            legislation['url'] = self.BASE_URL + \
                legislation_url.split('&Options')[0] + '&FullText=1'

            yield legislation

    def _advancedSearch(self, page):
        search_switcher = page.xpath(
            "//input[@id='ctl00_ContentPlaceHolder1_btnSwitch']")[0]

        if 'simple search' in search_switcher.value.lower():
            return page
        else:
            payload = self.sessionSecrets(page)
            payload[search_switcher.name] = search_switcher.value

            page = self.lxmlize(self.LEGISLATION_URL, payload)

            if 'simple search' not in page.xpath("//input[@id='ctl00_ContentPlaceHolder1_btnSwitch']")[0].value.lower():
                raise ValueError('Not on the advanced search page')

            return page

    def details(self, detail_url, div_id):
        detail_page = self.lxmlize(detail_url)

        detail_div = detail_page.xpath(".//div[@id='%s']" % div_id)[0]

        return self.parseDetails(detail_div)

    def legDetails(self, detail_url):
        div_id = 'ctl00_ContentPlaceHolder1_pageDetails'
        return self.details(detail_url, div_id)

    def actionDetails(self, detail_url):
        div_id = 'ctl00_ContentPlaceHolder1_pageTop1'
        return self.details(detail_url, div_id)

    def history(self, detail_url):
        detail_page = self.lxmlize(detail_url)

        try:
            history_table = detail_page.xpath(
                "//table[@id='ctl00_ContentPlaceHolder1_gridLegislation_ctl00']")[0]
        except IndexError:
            print(detail_url)
            raise

        history = [row[0] for row in self.parseDataTable(history_table)]

        try:
            history = sorted(history, key=self._actionSortKey)
        except (TypeError, ValueError):
            pass

        for action in history:
            yield action

    def _actionSortKey(self, action):
        action_date = self.toDate(action['Date'])
        action_url = action['Action\xa0Details']['url']

        return (action_date, action_url)

    def text(self, detail_url):
        detail_page = self.lxmlize(detail_url)

        text_div = detail_page.xpath(
            "//div[@id='ctl00_ContentPlaceHolder1_divText']")

        if len(text_div):
            return tostring(text_div[0], pretty_print=True).decode()
        else:
            return None

    def extractVotes(self, action_detail_url):
        action_detail_page = self.lxmlize(action_detail_url)
        try:
            vote_table = action_detail_page.xpath(
                "//table[@id='ctl00_ContentPlaceHolder1_gridVote_ctl00']")[0]
        except IndexError:
            self.warning("No votes found in table")
            return None, []
        votes = list(self.parseDataTable(vote_table))
        vote_list = []
        for vote, _, _ in votes:
            raw_option = vote['Vote'].lower()
            vote_list.append((self.VOTE_OPTIONS.get(raw_option, raw_option),
                              vote['Person Name']['label']))

        action_detail_div = action_detail_page.xpath(
            ".//div[@id='ctl00_ContentPlaceHolder1_pageTop1']")[0]
        action_details = self.parseDetails(action_detail_div)
        result = action_details['Result'].lower()

        return result, vote_list


def dateWithin(created_after, created_before):
    payload = dateBound(created_after)

    payload['ctl00$ContentPlaceHolder1$txtFileCreated2'] =\
        '{d.year}-{d.month:02}-{d.day:02}'.format(d=created_before)
    payload['ctl00$ContentPlaceHolder1$txtFileCreated2$dateInput'] =\
        '{d.month}/{d.day}/{d.year}'.format(d=created_before)

    payload['ctl00_ContentPlaceHolder1_txtFileCreated2_dateInput_ClientState'] =\
        '{{"enabled":true, "emptyMessage":"","validationText":"{d.year}-{d.month:02}-{d.day:02}-00-00-00","valueAsString":"{d.year}-{d.month:02}-{d.day:02}-00-00-00","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00", "lastSetTextBoxValue":"{d.month}/{d.day}/{d.year}"}}'.format( # noqa : E501
            d=created_before)

    payload['ctl00$ContentPlaceHolder1$radFileCreated'] = 'between'

    return payload


def dateBound(creation_date):
    payload = {}

    payload['ctl00$ContentPlaceHolder1$txtFileCreated1'] =\
        '{d.year}-{d.month:02}-{d.day:02}'.format(d=creation_date)
    payload['ctl00$ContentPlaceHolder1$txtFileCreated1$dateInput'] =\
        '{d.month}/{d.day}/{d.year}'.format(d=creation_date)

    payload['ctl00_ContentPlaceHolder1_txtFileCreated1_dateInput_ClientState'] =\
        '{{"enabled":true, "emptyMessage":"","validationText":"{d.year}-{d.month:02}-{d.day:02}-00-00-00","valueAsString":"{d.year}-{d.month:02}-{d.day:02}-00-00-00","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00", "lastSetTextBoxValue":"{d.month}/{d.day}/{d.year}"}}'.format( # noqa : E501
            d=creation_date)

    return payload


class LegistarAPIBillScraper(LegistarAPIScraper):
    def matters(self, since_datetime=None, scrape_restricted=False):

        # scrape from oldest to newest. This makes resuming big
        # scraping jobs easier because upon a scrape failure we can
        # import everything scraped and then scrape everything newer
        # then the last bill we scraped
        params = {'$orderby': 'MatterLastModifiedUtc'}

        if since_datetime:
            params['$filter'] = "MatterLastModifiedUtc gt datetime'{since_datetime}'".format(since_datetime=since_datetime.isoformat())

        matters_url = self.BASE_URL + '/matters'

        for matter in self.pages(matters_url,
                                 params=params,
                                 item_key="MatterId"):
            try:
                legistar_url = self.legislation_detail_url(matter['MatterId'])
            except KeyError:
                url = matters_url + '/{}'.format(matter['MatterId'])
                self.warning('Bill could not be found in web interface: {}'.format(url))
                if scrape_restricted:
                    yield matter
                else:
                    continue
            else:
                matter['legistar_url'] = legistar_url

            yield matter

    def matter(self, matter_id, scrape_restricted=False):
        matter = self.endpoint('/matters/{}', matter_id)

        try:
            legistar_url = self.legislation_detail_url(matter_id)
        except KeyError:
            url = self.BASE_URL + '/matters/{}'.format(matter_id)
            self.warning('Bill could not be found in web interface: {}'.format(url))
            if scrape_restricted:
                return matter
            else:
                return None
        else:
            matter['legistar_url'] = legistar_url

        return matter

    def endpoint(self, route, *args):
        url = self.BASE_URL + route
        response = self.get(url.format(*args))
        return response.json()

    topics = partialmethod(endpoint, '/matters/{0}/indexes')
    code_sections = partialmethod(endpoint, 'matters/{0}/codesections')

    def attachments(self, matter_id):
        attachments = self.endpoint('/matters/{0}/attachments', matter_id)

        unique_attachments = []
        scraped_urls = set()

        # Handle matters with duplicate attachments.
        for attachment in attachments:
            url = attachment['MatterAttachmentHyperlink']
            if url not in scraped_urls:
                unique_attachments.append(attachment)
                scraped_urls.add(url)

        return unique_attachments

    def votes(self, history_id):
        url = self.BASE_URL + '/eventitems/{0}/votes'.format(history_id)

        response = self.get(url)
        if self._missing_votes(response):
            return []
        else:
            return response.json()

    def history(self, matter_id):
        actions = self.endpoint('/matters/{0}/histories', matter_id)
        for action in actions:
            action['MatterHistoryActionName'] = action['MatterHistoryActionName'].strip()

        actions = sorted((action for action in actions
                          if (action['MatterHistoryActionDate'] and
                              action['MatterHistoryActionName'] and
                              action['MatterHistoryActionBodyName'])),
                         key=lambda action: action['MatterHistoryActionDate'])

        return actions

    def sponsors(self, matter_id):
        spons = self.endpoint('/matters/{0}/sponsors', matter_id)

        if spons:
            max_version = max(
                (sponsor['MatterSponsorMatterVersion'] for sponsor in spons),
                key=lambda version: self._version_rank(version)
            )

            spons = [sponsor for sponsor in spons
                     if sponsor['MatterSponsorMatterVersion'] == str(max_version)]

            return sorted(spons,
                          key=lambda sponsor: sponsor["MatterSponsorSequence"])

        else:
            return []

    def _version_rank(self, version):
        '''
        In general, matter versions are numbers. This method provides an
        override opportunity for handling versions that are not numbers.
        '''
        return int(version)

    def relations(self, matter_id):
        relations = self.endpoint('/matters/{0}/relations', matter_id)
        if relations:
            highest_flag = max(int(relation['MatterRelationFlag'])
                               for relation in relations)

            relations = [relation for relation in relations
                         if relation['MatterRelationFlag'] == highest_flag]

            return relations
        else:
            return []

    def text(self, matter_id):
        version_route = '/matters/{0}/versions'
        text_route = '/matters/{0}/texts/{1}'

        versions = self.endpoint(version_route, matter_id)

        latest_version = max(
            versions, key=lambda x: self._version_rank(x['Value']))

        text_url = self.BASE_URL + \
            text_route.format(matter_id, latest_version['Key'])
        response = self.get(text_url, stream=True)
        if int(response.headers['Content-Length']) < 21052630:
            return response.json()

    def legislation_detail_url(self, matter_id):
        gateway_url = self.BASE_WEB_URL + '/gateway.aspx?m=l&id={0}'

        legislation_detail_route = requests.head(
            gateway_url.format(matter_id)).headers['Location']

        return urljoin(self.BASE_WEB_URL, legislation_detail_route)

    def _missing_votes(self, response):
        # Handle no individual votes from vote event
        missing = (response.status_code == 500 and
                   response.json().get('InnerException', {}).get('ExceptionMessage', '') == "The cast to value type 'System.Int32' failed because the materialized value is null. Either the result type's generic parameter or the query must use a nullable type.") # noqa : 501
        return missing

    def accept_response(self, response, **kwargs):
        '''
        If we hit a missing votes page we don't need to keep retrying it.
        This overrides a method that controls whether the scraper
        should retry on an error.
        '''
        accept = (super().accept_response(response) or
                  self._missing_votes(response))
        return accept
