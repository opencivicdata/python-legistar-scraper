import time
import datetime
from collections import deque

import lxml.html
import pytz
import icalendar
import requests
from pupa.scrape import Scraper
import scrapelib

from .base import LegistarScraper, LegistarAPIScraper


class LegistarEventsScraper(LegistarScraper):
    def eventPages(self, since) :
        # Directly use the requests library here, so that we do not
        # use a cached page, which may have expired .NET state values,
        # even in fastmode (which uses the cache).
        response = requests.get(self.EVENTSPAGE, verify=False)
        self._check_errors(response)
        entry = response.text
        page = lxml.html.fromstring(entry)
        page.make_links_absolute(self.EVENTSPAGE)

        if since is None :
            for page in self.eventSearch(page, 'All'):
                # time_range, = page.xpath("//input[@id='ctl00_ContentPlaceHolder1_lstYears_Input']")
                # time_range = time_range.value
                # assert time_range == "All Years"
                yield page
        else :
            for year in range(since, self.now().year + 1) :
                yield from self.eventSearch(page, str(year))

    def eventSearch(self, page, value) :
        payload = self.sessionSecrets(page)

        payload['ctl00_ContentPlaceHolder1_lstYears_ClientState'] = '{"value":"%s"}' % value

        payload['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$lstYears'

        return self.pages(self.EVENTSPAGE, payload)

    def events(self, follow_links=True, since=None) :
        # If an event is added to the the legistar system while we
        # are scraping, it will shift the list of events down and
        # we might revisit the same event. So, we keep track of
        # the last few events we've visited in order to
        # make sure we are not revisiting
        scraped_events = deque([], maxlen=10)

        for page in self.eventPages(since) :

            events_table = page.xpath("//table[@class='rgMasterTable']")[0]
            for event, _, _ in self.parseDataTable(events_table) :
                if follow_links and type(event["Meeting Details"]) == dict :
                    detail_url = event["Meeting Details"]['url']
                    if detail_url in scraped_events :
                        continue
                    else :
                        scraped_events.append(detail_url)

                    meeting_details = self.lxmlize(detail_url)

                    agenda = self.agenda(detail_url)

                else :
                    agenda = None
                
                yield event, agenda

    def agenda(self, detail_url) :
        page = self.lxmlize(detail_url)

        payload = self.sessionSecrets(page)

        payload.update({"__EVENTARGUMENT": "3:1",
                        "__EVENTTARGET":"ctl00$ContentPlaceHolder1$menuMain"})
        
        for page in self.pages(detail_url, payload) :
            agenda_table = page.xpath(
                "//table[@id='ctl00_ContentPlaceHolder1_gridMain_ctl00']")[0]
            agenda = self.parseDataTable(agenda_table)
            yield from agenda

    def addDocs(self, e, events, doc_type) :
        try :
            if events[doc_type] != 'Not\xa0available' : 
                e.add_document(note= events[doc_type]['label'],
                               url = events[doc_type]['url'],
                               media_type="application/pdf")
        except ValueError :
            pass

    def extractRollCall(self, action_detail_url) :
        action_detail_page = self.lxmlize(action_detail_url)
        try:
            rollcall_table = action_detail_page.xpath("//table[@id='ctl00_ContentPlaceHolder1_gridRollCall_ctl00']")[0]
        except IndexError:
            self.warning("No rollcall found in table")
            return []
        roll_call = list(self.parseDataTable(rollcall_table))
        call_list = []
        for call, _, _ in roll_call :
            option = call['Attendance']
            call_list.append((option,
                              call['Person Name']['label']))

        return call_list


    def ical(self, ical_text):
        value = icalendar.Calendar.from_ical(ical_text)
        return value
        


class LegistarAPIEventScraper(LegistarAPIScraper):

    def events(self, since_datetime=None):
        if since_datetime:
            params = {'$filter' : "EventLastModifiedUtc gt datetime'{since_datetime}'".format(since_datetime = since_datetime.isoformat())}
        else:
            params = {}

        events_url = self.BASE_URL + '/events/'

        web_results = self._scrapeWebCalendar()

        for api_event in self.pages(events_url,
                                    params=params,
                                    item_key="EventId"):
            start = self.toTime(api_event['EventDate'])
            # EventTime may be 'None': this try-except block catches those instances.
            try:
                start_time = time.strptime(api_event['EventTime'], '%I:%M %p')
            except TypeError:
                continue
            else:
                api_event['start'] = start.replace(hour=start_time.tm_hour,
                                                   minute=start_time.tm_min)
                api_event['status'] = confirmed_or_passed(api_event['start'])

                key = (api_event['EventBodyName'].strip(),
                       api_event['start'])

                try:
                    web_event = web_results[key]
                    yield api_event, web_event
                except KeyError:
                    continue
            

    def agenda(self, event):
        agenda_url = self.BASE_URL + '/events/{}/eventitems'.format(event['EventId'])

        response = self.get(agenda_url)

        try:
            # Order the event items according to the EventItemMinutesSequence. If an 
            # event item does not have a value for EventItemMinutesSequence, the script 
            #will throw a TypeError. In that case, try to order by EventItemAgendaSequence.
            filtered_response = sorted((item for item in response.json() 
                                        if item['EventItemTitle']), 
                                       key = lambda item : item['EventItemMinutesSequence'])
        except TypeError:
            try:
                filtered_response = sorted((item for item in response.json() 
                                            if item['EventItemTitle']), 
                                           key = lambda item : item['EventItemAgendaSequence'])
            except TypeError:
                filtered_response = (item for item in response.json() 
                                     if item['EventItemTitle'])

        for item in filtered_response:
            yield item

    def rollcalls(self, event):
        for item in self.agenda(event):
            if item['EventItemRollCallFlag']:
                rollcall_url = self.BASE_URL + '/eventitems/{}/rollcalls'.format(item['EventItemId'])

                response = self.get(rollcall_url)

                for item in response.json():
                    yield item

    def _scrapeWebCalendar(self):
        web_scraper = LegistarEventsScraper(self.jurisdiction,
                                            self.datadir,
                                            strict_validation=self.strict_validation,
                                            fastmode=(self.requests_per_minute == 0))
        web_scraper.EVENTSPAGE = self.EVENTSPAGE
        web_scraper.BASE_URL = self.WEB_URL
        web_scraper.TIMEZONE = self.TIMEZONE
        web_scraper.date_format = '%m/%d/%Y'

        web_info = {}

        for event, _ in web_scraper.events(follow_links=False):
            # Make the dict key (name, datetime.datetime), and add it.
            response = self.get(event['iCalendar']['url'], verify=False)
            web_scraper._check_errors(response)
            event_time = web_scraper.ical(response.text).subcomponents[0]['DTSTART'].dt
            event_time = pytz.timezone(self.TIMEZONE).localize(event_time)

            key = (event['Name']['label'],
                   event_time)
            web_info[key] = event

        return web_info

    def addDocs(self, e, events, doc_type):
        try :
            if events[doc_type] != 'Not\xa0available':
                e.add_document(note= events[doc_type]['label'],
                               url = events[doc_type]['url'],
                               media_type="application/pdf")
        except ValueError :
            pass


    
def confirmed_or_passed(when) :
    if datetime.datetime.utcnow().replace(tzinfo = pytz.utc) > when :
        status = 'confirmed'
    else :
        status = 'passed'
    
    return status

