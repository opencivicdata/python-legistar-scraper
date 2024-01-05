from abc import ABCMeta, abstractmethod
import time
import datetime
from collections import deque
import esprima

import pytz
import icalendar
import scrapelib

from .base import LegistarScraper, LegistarAPIScraper


class LegistarEventsScraper(LegistarScraper):
    ECOMMENT_JS_URLS = (
        'https://metro.granicusideas.com/meetings.js',
        'https://metro.granicusideas.com/meetings.js?scope=past'
    )

    def __init__(self, *args, event_info_key='Meeting Details', **kwargs):
        super().__init__(*args, **kwargs)
        self.event_info_key = event_info_key


    @property
    def ecomment_dict(self):
        """
        Parse event IDs and eComment links from JavaScript file with lines like:
        activateEcomment('750', '138A085F-0AC1-4A33-B2F3-AC3D6D9F710B', 'https://metro.granicusideas.com/meetings/750-finance-budget-and-audit-committee-on-2020-03-16-5-00-pm-test');
        """
        if getattr(self, '_ecomment_dict', None) is None:
            ecomment_dict = {}

            # Define a callback to apply to each node, e.g.,
            # https://esprima.readthedocs.io/en/latest/syntactic-analysis.html#example-console-calls-removal
            def is_activateEcomment(node, metadata):
                if node.callee and node.callee.name == 'activateEcomment':
                    event_id, _, comment_url = node.arguments
                    ecomment_dict[event_id.value] = comment_url.value

            for url in self.ECOMMENT_JS_URLS:
                response = self.get(url)
                esprima.parse(response.text, delegate=is_activateEcomment)

            self._ecomment_dict = ecomment_dict

        return self._ecomment_dict

    def eventPages(self, since):

        page = self.lxmlize(self.EVENTSPAGE)
        for page in self.eventSearch(page, since):
            yield page

    def should_cache_response(self, response):
        # Never cache the top level events page, because that may result in
        # expired .NET state values.
        return (super().should_cache_response(response) and
                response.url != self.EVENTSPAGE)

    def eventSearch(self, page, since):
        payload = self.sessionSecrets(page)

        payload['ctl00_ContentPlaceHolder1_lstYears_ClientState'] = '{"value":"%s"}' % since

        payload['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$lstYears'

        return self.pages(self.EVENTSPAGE, payload)

    def events(self, follow_links=True, since=None):
        # If an event is added to the the legistar system while we
        # are scraping, it will shift the list of events down and
        # we might revisit the same event. So, we keep track of
        # the last few events we've visited in order to
        # make sure we are not revisiting
        scraped_events = deque([], maxlen=10)

        current_year = self.now().year

        if since:
            if since > current_year:
                raise ValueError(
                    'Value of :since cannot exceed {}'.format(current_year))
            else:
                since_year = since - 1

        else:
            since_year = 0

        # Anticipate events will be scheduled for the following year to avoid
        # missing upcoming events during scrapes near the end of the current
        # year.
        for year in range(current_year + 1, since_year, -1):
            no_events_in_year = True

            for page in self.eventPages(year):
                events_table = page.xpath("//div[@id='ctl00_ContentPlaceHolder1_MultiPageCalendar']//table[@class='rgMasterTable']")[0]
                for event, _, _ in self.parseDataTable(events_table):
                    ical_url = event['iCalendar']['url']
                    if ical_url in scraped_events:
                        continue
                    else:
                        scraped_events.append(ical_url)

                    if follow_links and type(event[self.event_info_key]) == dict:
                        agenda = self.agenda(event[self.event_info_key]['url'])
                    else:
                        agenda = None

                    yield event, agenda
                    no_events_in_year = False

            # We scrape events in reverse chronological order, starting one year
            # in the future. Stop scraping if there are no events in a given
            # year, unless that year is in the future, because whether events
            # have been scheduled in the future is not a reliable indication of
            # whether any happened in the previous year.
            if no_events_in_year and year <= current_year:
                break

    def agenda(self, detail_url):
        page = self.lxmlize(detail_url)

        payload = self.sessionSecrets(page)

        payload.update({"__EVENTARGUMENT": "3:1",
                        "__EVENTTARGET": "ctl00$ContentPlaceHolder1$menuMain"})

        for page in self.pages(detail_url, payload):
            agenda_table = page.xpath(
                "//table[@id='ctl00_ContentPlaceHolder1_gridMain_ctl00']")[0]
            agenda = self.parseDataTable(agenda_table)
            yield from agenda

    def addDocs(self, e, events, doc_type):
        try:
            if events[doc_type] != 'Not\xa0available':
                e.add_document(note=events[doc_type]['label'],
                               url=events[doc_type]['url'],
                               media_type="application/pdf")
        except ValueError:
            pass

    def extractRollCall(self, action_detail_url):
        action_detail_page = self.lxmlize(action_detail_url)
        try:
            rollcall_table = action_detail_page.xpath(
                "//table[@id='ctl00_ContentPlaceHolder1_gridRollCall_ctl00']")[0]
        except IndexError:
            self.warning("No rollcall found in table")
            return []
        roll_call = list(self.parseDataTable(rollcall_table))
        call_list = []
        for call, _, _ in roll_call:
            option = call['Attendance']
            call_list.append((option,
                              call['Person Name']['label']))

        return call_list

    def ical(self, ical_text):
        value = icalendar.Calendar.from_ical(ical_text)
        return value

    def _parse_detail(self, key, field_1, field_2):
        if key == 'eComment':
            return self._get_ecomment_link(field_2) or field_2.text_content().strip()

    def _get_ecomment_link(self, link):
        event_id = link.attrib['data-event-id']
        return self.ecomment_dict.get(event_id, None)


class LegistarAPIEventScraperBase(LegistarAPIScraper, metaclass=ABCMeta):
    webscraper_class = LegistarEventsScraper
    WEB_RETRY_EVENTS = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._webscraper = self._init_webscraper()

    def _init_webscraper(self):
        webscraper = self.webscraper_class(
            requests_per_minute=self.requests_per_minute,
            retry_attempts=self.WEB_RETRY_EVENTS)

        if self.cache_storage:
            webscraper.cache_storage = self.cache_storage

        webscraper.cache_write_only = self.cache_write_only

        webscraper.BASE_URL = self.WEB_URL
        webscraper.EVENTSPAGE = self.EVENTSPAGE
        webscraper.BASE_URL = self.WEB_URL
        webscraper.TIMEZONE = self.TIMEZONE
        webscraper.date_format = '%m/%d/%Y'

        return webscraper

    @abstractmethod
    def _get_web_event(self, api_event):
        pass

    def api_events(self, since_datetime=None):
        # scrape from oldest to newest. This makes resuming big
        # scraping jobs easier because upon a scrape failure we can
        # import everything scraped and then scrape everything newer
        # then the last event we scraped
        params = {'$orderby': 'EventLastModifiedUtc'}

        if since_datetime:
            # We include events three days before the given start date
            # to make sure we grab updated fields (e.g. audio recordings)
            # that don't update the last modified timestamp.
            backwards_window = datetime.timedelta(hours=72)
            since_iso = (since_datetime - backwards_window).isoformat()

            # Minutes are often published after an event occurs – without a
            # corresponding event modification. Query all update fields so later
            # changes are always caught by our scraper, particularly when
            # scraping narrower windows of time.
            update_fields = ('EventDate',
                             'EventLastModifiedUtc',
                             'EventAgendaLastPublishedUTC',
                             'EventMinutesLastPublishedUTC')

            since_fmt = "{field} gt datetime'{since_datetime}'"
            since_filter =\
                ' or '.join(since_fmt.format(field=field,
                                             since_datetime=since_iso)
                            for field in update_fields)

            params['$filter'] = since_filter

        events_url = self.BASE_URL + '/events/'

        yield from self.pages(events_url,
                              params=params,
                              item_key="EventId")

    def events(self, since_datetime=None):
        for api_event in self.api_events(since_datetime=since_datetime):

            time_str = api_event['EventTime']
            if not time_str:  # If we don't have an event time, skip it
                continue

            try:
                # Start times are entered manually. Sometimes, they don't
                # conform to this format. Log events with invalid start times,
                # but don't interrupt the scrape for them.
                start_time = time.strptime(time_str, self.time_string_format)
            except ValueError:
                event_url = '{0}/events/{1}'.format(self.BASE_URL, api_event['EventId'])
                self.logger.error('API event has invalid start time "{0}": {1}'.format(time_str, event_url))
                continue

            start = self.toTime(api_event['EventDate'])
            api_event['start'] = start.replace(hour=start_time.tm_hour,
                                               minute=start_time.tm_min)

            api_event['status'] = self._event_status(api_event)

            web_event = self._get_web_event(api_event)

            if web_event:
                yield api_event, web_event

            else:
                event_url = '{0}/events/{1}'.format(self.BASE_URL, api_event['EventId'])
                self.warning('API event could not be found in web interface: {0}'.format(event_url))
                continue

    def agenda(self, event):
        agenda_url = (self.BASE_URL +
                      '/events/{}/eventitems'.format(event['EventId']))

        response = self.get(agenda_url)

        # If an event item does not have a value for
        # EventItemAgendaSequence, it is not on the agenda
        filtered_items = (item for item in response.json()
                          if (item['EventItemTitle'] and
                              item['EventItemAgendaSequence']))
        sorted_items = sorted(filtered_items,
                              key=lambda item: item['EventItemAgendaSequence'])

        for item in sorted_items:
            self._suppress_item_matter(item, agenda_url)
            yield item

    def minutes(self, event):
        minutes_url = (self.BASE_URL +
                       '/events/{}/eventitems'.format(event['EventId']))

        response = self.get(minutes_url)

        # If an event item does not have a value for
        # EventItemMinutesSequence, it is not in the minutes
        filtered_items = (item for item in response.json()
                          if (item['EventItemTitle'] and
                              item['EventItemMinutesSequence']))
        sorted_items = sorted(filtered_items,
                              key=lambda item: item['EventItemMinutesSequence'])

        for item in sorted_items:
            self._suppress_item_matter(item, minutes_url)
            yield item

    def _suppress_item_matter(self, item, agenda_url):
        '''
        Agenda items in Legistar do not always display links to
        associated matter files even if the same agenda item
        in the API references a Matter File. The agenda items
        we scrape should honor the suppression on the Legistar
        agendas.

        This is also practical because matter files that are hidden
        in the Legistar Agenda do not seem to available for scraping
        on Legistar or through the API

        Since we are not completely sure that the same suppression
        logic should be used for all Legislative Bodies, this method
        is currently just a hook for being overridden in particular
        scrapers. As of now, at least LA Metro uses this hook.
        '''
        pass

    def rollcalls(self, event):
        for item in self.agenda(event):
            if item['EventItemRollCallFlag']:
                rollcall_url = self.BASE_URL + \
                    '/eventitems/{}/rollcalls'.format(item['EventItemId'])

                response = self.get(rollcall_url)

                for item in response.json():
                    yield item

    def addDocs(self, e, events, doc_type):
        try:
            if events[doc_type] != 'Not\xa0available':
                e.add_document(note=events[doc_type]['label'],
                               url=events[doc_type]['url'],
                               media_type="application/pdf")
        except ValueError:
            pass

    def _event_status(self, event):
        '''Events can have a status of tentative, confirmed, cancelled, or
        passed (http://docs.opencivicdata.org/en/latest/data/event.html). By
        default, set status to passed if the current date and time exceeds the
        event date and time, or confirmed otherwise. Available for override in
        jurisdictional scrapers.
        '''
        if datetime.datetime.utcnow().replace(tzinfo=pytz.utc) > event['start']:
            status = 'passed'
        else:
            status = 'confirmed'

        return status


class LegistarAPIEventScraper(LegistarAPIEventScraperBase):

    def _get_web_event(self, api_event):
        return self.web_detail(api_event)

    def web_detail(self, event):
        '''
        Grabs the information for an event from the Legistar website
        and returns as a dictionary.
        '''
        insite_url = event['EventInSiteURL']

        try:
            event_page = self._webscraper.lxmlize(insite_url)
        except scrapelib.HTTPError as e:
            if e.response.status_code == 410:
                return None
            else:
                raise

        div_id = 'ctl00_ContentPlaceHolder1_pageTop1'
        detail_div = event_page.xpath(".//div[@id='%s']" % div_id)[0]

        event_page_details = self._webscraper.parseDetails(detail_div)
        event_page_details['Meeting Details'] = {'url': insite_url}

        return event_page_details


class LegistarAPIEventScraperZip(LegistarAPIEventScraperBase):
    '''
    There are some inSite sites that have information that only appears
    event listing page, like NYC's 'Meeting Topic.' This scraper visits
    the listing page and attempts to zip API and web events together
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set attribute equal to an instance of our generator yielding events
        # scraped from the Legistar web interface. This allows us to pause
        # and resume iteration as needed.
        self._events = self._scrapeWebCalendar()

        # Instantiate dictionary where events from generator are stored as they
        # are scraped.
        self._scraped_events = {}

    def _get_web_event(self, api_event):
        if self._not_in_web_interface(api_event):
            return None
        else:
            # None if entire web calendar scraped but API event not found
            return self.web_results(api_event)

    def web_results(self, event):
        api_key = (event['EventBodyName'].strip(),
                   event['start'])

        # Check the cache of events we've already scraped from the web interface
        # for the API event at hand.
        if api_key in self._scraped_events:
            return self._scraped_events[api_key]

        else:
            # If API event not in web scrape cache, continue scraping the web
            # interface.
            for web_key, event in self._events:
                self._scraped_events[web_key] = event
                # When we find the API event, stop scraping.
                if web_key == api_key:
                    return event

    def _scrapeWebCalendar(self):
        '''Generator yielding events from Legistar in roughly reverse
        chronological order.
        '''
        for event, _ in self._webscraper.events(follow_links=False):
            event_key = self._event_key(event, self._webscraper)
            yield event_key, event

    def _event_key(self, event, web_scraper):
        '''Since Legistar InSite contains more information about events than
        are available in the API, we need to scrape both. Then, we have
        to line them up. This method makes a key that should be
        uniquely identify every event and will allow us to link
        events from the two data sources.
        '''
        response = web_scraper.get(event['iCalendar']['url'], verify=False)
        event_time = web_scraper.ical(response.text).subcomponents[0]['DTSTART'].dt
        event_time = pytz.timezone(self.TIMEZONE).localize(event_time)

        key = (event['Name']['label'],
               event_time)

        return key

    def _not_in_web_interface(self, event):
        '''Occasionally, an event will appear in the API, but not in the web
        interface. This method checks attributes of the API event that tell us
        whether the given event is one of those cases, returning True if so, and
        False otherwise. Available for override in jurisdictional scrapers.
        '''
        return False
