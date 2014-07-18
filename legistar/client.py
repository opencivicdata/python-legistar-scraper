import logging
import time
import random
import lxml.html
import contextlib

from requests.exceptions import ConnectionError
from hercules import DictSetDefault

from legistar.base import Base


class Client(Base):
    '''This object handles sending GET and POST requests and maintains
    the weird ASPX client state nonsense.
    '''
    CONNECTION_ERROR_SLEEP = 15

    def __init__(self):
        self.state = dict.fromkeys((
            '__EVENTVALIDATION',
            '__VIEWSTATE',
            '__EVENTTARGET',
            '__EVENTARGUMENT',
            ))

    def sleep(self):
        '''Disabled by default, because the main use of this scraper
        is with pupa, which defines it's own session object that transparently
        handles throttling, retires, etc.
        '''
        if self.cfg.DO_CLIENT_SLEEP:
            sleeptime = random.randint(*self.cfg.SLEEP_RANGE) / 100.0
            time.sleep(sleeptime)

    def check_resp(self, resp):
        '''Complain/log if response is anything other than OK.
        '''
        if resp.status_code != 200:
            msg = 'Error fetching page [%d]: %s'
            args = (resp.status_code, resp.text)
            self.critical(msg, *args)
            raise Exception(msg % args)

    def update_state(self, resp):
        '''Get the weird ASPX client state nonsense from the response
        and update the Client's state so it can be sent with future requests.
        '''
        doc = lxml.html.fromstring(resp.text)
        form = dict(doc.forms[0].fields)
        for key in self.state.keys() & form.keys():
            self.state[key] = form.get(key)

    def retry(self, method, *args, **kwargs):
        '''Sometimes Legistar will S the bed and drop the connection.
        That's probably because the crawl rate is too high. Sleeps for 2
        seconds then tries again.
        '''
        NUM_RETRIES = 1
        for _ in range(NUM_RETRIES):
            try:
                return method(*args, **kwargs)
            except ConnectionError as exc:
                self.exc = exc
                self.exception(exc)
                msg = 'Client got connection error. Sleeping %d seconds.'
                self.warning(msg % self.CONNECTION_ERROR_SLEEP)
                time.sleep(self.CONNECTION_ERROR_SLEEP)
        raise self.exc

    def get(self, url, **kwargs):
        '''Send a POST request, check it, update state, and sleep.
        '''
        _kwargs = dict(self.cfg.requests_kwargs)
        _kwargs.update(kwargs)
        resp = self.retry(self.session.get, url, **_kwargs)
        self.check_resp(resp)
        self.update_state(resp)
        self.sleep()
        return resp

    def head(self, url, **kwargs):
        '''Send a HEAD request. For getting mimetypes of documents.
        '''
        _kwargs = dict(self.cfg.requests_kwargs)
        _kwargs.update(kwargs)
        resp = self.retry(self.session.head, url, **_kwargs)
        self.check_resp(resp)
        self.sleep()
        return resp

    def post(self, url, data=None, extra_headers=None, **kwargs):
        '''Send a POST request, check it, update state, and sleep.
        '''
        _kwargs = dict(self.cfg.requests_kwargs)
        with DictSetDefault(_kwargs, 'headers', {}) as headers:
            headers.update(extra_headers or {})
        _kwargs.update(kwargs)
        _data = dict(self.state)

        # We need to include self.state in the post data, but do it first
        # so that passed-in data can overrite state params, like event target.
        if data is not None:
            _data.update(data or {})

        resp = self.retry(self.session.post, url, _data, **_kwargs)
        self.check_resp(resp)
        self.update_state(resp)
        self.sleep()
        return resp
