from .base import LegistarScraper

class LegistarEventsScraper(LegistarScraper):
    def eventPages(self, search_type='all') :

        page = self.lxmlize(self.EVENTSPAGE)

        if search_type == 'all' :
            payload = self.sessionSecrets(page)

            payload['ctl00$ContentPlaceHolder1$lstYears'] = 'All Years'
            payload['ctl00_ContentPlaceHolder1_lstYears_ClientState'] = '{"logEntries":[],"value":"All","text":"All Years","enabled":true,"checkedIndices":[],"checkedItemsTextOverflows":false}'


            payload['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$lstYears'

            return self.pages(self.EVENTSPAGE, payload)

        else :
            return self.pages(page)


    def events(self, follow_links=True) :
        for page in self.eventPages() :
            events_table = page.xpath("//table[@class='rgMasterTable']")[0]
            for events, headers, rows in self.parseDataTable(events_table) :
                if follow_links and type(events["Meeting Details"]) == dict :
                    detail_url = events["Meeting Details"]['url']
                    meeting_details = self.lxmlize(detail_url)

                    agenda_table = meeting_details.xpath(
                        "//table[@id='ctl00_ContentPlaceHolder1_gridMain_ctl00']")[0]
                    agenda = self.parseDataTable(agenda_table)

                else :
                    agenda = None
                
                yield events, agenda


    def addDocs(self, e, events, doc_type) :
        try :
            if events[doc_type] != 'Not\xa0available' : 
                e.add_document(note= events[doc_type]['label'],
                               url = events[doc_type]['url'],
                               media_type="application/pdf")
        except ValueError :
            pass
