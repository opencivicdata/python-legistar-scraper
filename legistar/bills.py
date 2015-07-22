from .base import LegistarScraper

class LegistarBillScraper(LegistarScraper):
    def searchLegislation(self, search_text='', created_after=None,
                          created_before=None, num_pages = None):
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
        payload['ctl00$ContentPlaceHolder1$btnSearch'] = 'Search Legislation'
        payload['ctl00$ContentPlaceHolder1$lstYearsAdvanced'] = 'All Years'


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
            legislation['url'] = self.BASE_URL + legislation_url.split('&Options')[0]

            yield legislation

    def _advancedSearch(self, page) :
        search_switcher = page.xpath("//input[@id='ctl00_ContentPlaceHolder1_btnSwitch']")[0]

        if 'Simple search' in search_switcher.value :
            return page
        else :
            payload = {}
            payload[search_switcher.name] = search_switcher.value
            payload.update(self.sessionSecrets(page))

            page = self.lxmlize(self.LEGISLATION_URL, payload)

            print(page.xpath("//input[@id='ctl00_ContentPlaceHolder1_btnSwitch']")[0].attrib)
            if 'Simple search' not in page.xpath("//input[@id='ctl00_ContentPlaceHolder1_btnSwitch']")[0].value :
                raise ValueError('Not on the advanced search page')

            return page

            
            

#<input type="submit" name="ctl00$ContentPlaceHolder1$btnSwitch" value="<<< Simple search" id="ctl00_ContentPlaceHolder1_btnSwitch" class="searchButton" style="font-family: Tahoma; font-size: 10pt; color: #333333;">

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
