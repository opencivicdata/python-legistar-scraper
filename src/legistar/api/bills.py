from functools import partialmethod
from urllib.parse import urljoin

import requests
import scrapelib

from .base import LegistarAPIScraper


class LegistarAPIBillScraper(LegistarAPIScraper):
    def __init__(self, *args, **kwargs):
        '''
        Initialize the Bill scraper with a `scrape_restricted` property.
        Do not collect private bills (i.e., bills with 'MatterRestrictViewViaWeb'
        set as True in the API), unless the scrapers have access to them,
        e.g., via a token.
        '''
        super().__init__(*args, **kwargs)

        self.scrape_restricted = False

    def matters(self, since_datetime=None):
        # scrape from oldest to newest. This makes resuming big
        # scraping jobs easier because upon a scrape failure we can
        # import everything scraped and then scrape everything newer
        # then the last bill we scraped
        params = {'$orderby': 'MatterLastModifiedUtc'}

        if since_datetime:
            since_iso = since_datetime.isoformat()

            update_fields = ('MatterLastModifiedUtc',
                             'MatterIntroDate',
                             'MatterPassedDate',
                             'MatterDate1',
                             'MatterDate2',
                             # 'MatterEXDate1', # can't use all 17 search
                             # terms, this one always
                             # seems to be not set
                             'MatterEXDate2',
                             'MatterEXDate3',
                             'MatterEXDate4',
                             'MatterEXDate5',
                             'MatterEXDate6',
                             'MatterEXDate7',
                             'MatterEXDate8',
                             'MatterEXDate9',
                             'MatterEXDate10',
                             'MatterEnactmentDate',
                             'MatterAgendaDate')

            since_fmt = "{field} gt datetime'{since_datetime}'"
            since_filter =\
                ' or '.join(since_fmt.format(field=field,
                                             since_datetime=since_iso)
                            for field in update_fields)

            params['$filter'] = since_filter

        matters_url = self.BASE_URL + '/matters'

        for matter in self.pages(matters_url,
                                 params=params,
                                 item_key="MatterId"):
            try:
                legistar_url = self.legislation_detail_url(matter['MatterId'])

            except scrapelib.HTTPError as e:
                if e.response.status_code > 403:
                    raise

                url = matters_url + '/{}'.format(matter['MatterId'])
                self.warning('Bill could not be found in web interface: {}'.format(url))
                if not self.scrape_restricted:
                    continue

            else:
                matter['legistar_url'] = legistar_url

            yield matter

    def matter(self, matter_id):
        matter = self.endpoint('/matters/{}', matter_id)

        try:
            legistar_url = self.legislation_detail_url(matter_id)
        except scrapelib.HTTPError as e:
            if e.response.status_code > 403:
                raise

            url = self.BASE_URL + '/matters/{}'.format(matter_id)
            self.warning('Bill could not be found in web interface: {}'.format(url))
            if not self.scrape_restricted:
                return None

        else:
            matter['legistar_url'] = legistar_url

        return matter

    def endpoint(self, route, *args):
        url = self.BASE_URL + route
        response = self.get(url.format(*args))
        return response.json()

    code_sections = partialmethod(endpoint, 'matters/{0}/codesections')

    def topics(self, *args, **kwargs):
        if args:
            return self.endpoint('/matters/{0}/indexes', *args)
        else:
            matter_indexes_url = self.BASE_URL + '/indexes'
            return self.pages(matter_indexes_url,
                              params=kwargs,
                              item_key="IndexId")

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

        try:
            response = self.get(url)
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return []
            else:
                raise

        if self._missing_votes(response):
            return []
        else:
            return response.json()

    def history(self, matter_id):
        actions = self.endpoint('/matters/{0}/histories', matter_id)
        for action in actions:
            action['MatterHistoryActionName'] = (
                action['MatterHistoryActionName'].strip()
            )

        actions = sorted((action for action in actions
                          if (action['MatterHistoryActionDate']
                              and action['MatterHistoryActionName']
                              and action['MatterHistoryActionBodyName'])),
                         key=lambda action: action['MatterHistoryActionDate'])

        # sometimes there are exact duplicates of actions. while this
        # is a a data entry problem that ideally the source system
        # would fix, they ain't always the way the world works.
        #
        # so, remove adjacent duplicate items.
        uniq_actions = []

        previous_key = None
        for action in actions:
            # these are the attributes that pupa uses for
            # checking for duplicate vote events
            current_key = (action['MatterHistoryActionName'],
                           action['MatterHistoryActionBodyName'])
            if current_key != previous_key:
                uniq_actions.append(action)
                previous_key = current_key
            else:
                self.warning(
                    '"{0} by {1}" appears more than once in '
                    '{2}/matters/{3}/histories. Duplicate actions have been '
                    'removed.'.format(
                        current_key[0],
                        current_key[1],
                        self.BASE_URL,
                        matter_id))

        return uniq_actions

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
            return self._filter_relations(relations)

        else:
            return []

    def _filter_relations(self, relations):
        '''
        Sometimes, many versions of a bill are related. This method returns the
        most recent version of each relation. Override this method to apply a
        different filter or return the full array of relations.
        '''
        # Sort relations such that the latest version of each matter
        # ID is returned first.
        sorted_relations = sorted(
            relations,
            key=lambda x: (
                x['MatterRelationMatterId'],
                x['MatterRelationFlag']
            ),
            reverse=True
        )

        seen_relations = set()

        for relation in sorted_relations:
            relation_id = relation['MatterRelationMatterId']

            if relation_id not in seen_relations:
                yield relation
                seen_relations.add(relation_id)

    def text(self, matter_id, latest_version_value=None):
        '''Historically, we have determined the latest version of a bill
        by finding the version with the highest value (either numerical
        or alphabetical).

        However, the `MatterVersion` field on the matter detail page
        most accurately identifies the latest version of a bill.
        This proves to be true for Metro, in particular.

        Other municipalities may share this characteristic with Metro.
        Until we know more, the `text` function accepts `latest_version_value`,
        i.e., matter['MatterVersion'], as an optional argument.'''

        version_route = '/matters/{0}/versions'
        text_route = '/matters/{0}/texts/{1}'

        versions = self.endpoint(version_route, matter_id)

        if latest_version_value:
            latest_version = next(
                version for version
                in versions
                if version['Value'] == latest_version_value)
        else:
            latest_version = max(
                versions, key=lambda x: self._version_rank(x['Value']))

        text_url = self.BASE_URL + \
            text_route.format(matter_id, latest_version['Key'])
        response = self.get(text_url, stream=True)
        if int(response.headers['Content-Length']) < 21052630:
            return response.json()

    def legislation_detail_url(self, matter_id):
        gateway_url = self.BASE_WEB_URL + '/gateway.aspx?m=l&id={0}'.format(matter_id)

        # We want to supress any session level params for this head request,
        # since they could lead to an additonal level of redirect.
        #
        # Per
        # http://docs.python-requests.org/en/master/user/advanced/, we
        # have to do this by setting session level params to None
        response = self.head(
            gateway_url,
            params={k: None for k in self.params}
        )

        # If the gateway URL redirects, the matter is publicly viewable. Grab
        # its detail URL from the response headers.
        if response.status_code == 302:
            legislation_detail_route = response.headers['Location']
            return urljoin(self.BASE_WEB_URL, legislation_detail_route)

        # If the gateway URL returns a 200, it has not redirected, i.e., the
        # matter is not publicly viewable. Return an unauthorized response.
        elif response.status_code == 200:
            response.status_code = 403
            raise scrapelib.HTTPError(response)

        # If the status code is anything but a 200 or 302, something is wrong.
        # Raise an HTTPError to interrupt the scrape.
        else:
            self.error(
                '{0} returned an unexpected status code: {1}'.format(
                    gateway_url, response.status_code
                )
            )
            response.status_code = 500
            raise scrapelib.HTTPError(response)

    def _missing_votes(self, response):
        '''
        Check to see if a response has the particular status code and
        error message that corresponds to inaccessible eventitem votes.

        see `accept_response` for more discussion of why we are doing this.
        '''
        missing = (response.status_code == 500
                   and response.json().get('InnerException', {}).get(
                       'ExceptionMessage', '') == (
                       "The cast to value type 'System.Int32' failed because the "
                       "materialized value is null. Either the result type's "
                       "generic parameter or the query must use a nullable type."
                   ))
        return missing

    def accept_response(self, response, **kwargs):
        '''
        Sometimes there ought to be votes on an eventitem but when we
        visit the votes page, the API returns a 500 status code and a
        particular error message.

        Typically, on 500 errors, we'll retry a few times because the
        errors are often transient. In this particular case, the errors
        are never transient.

        This happens frequently. If we retried on all those
        cases, it would really slow down the scraping. To avoid that
        we short circuit scrapelib's retry mechanism for this particular
        error.
        '''
        accept = (super().accept_response(response)
                  or self._missing_votes(response)
                  or response.status_code <= 403)
        return accept
