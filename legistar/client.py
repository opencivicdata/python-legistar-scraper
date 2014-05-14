import logging
import time
import random
import lxml.html


class Client:

    SLEEP = True

    def __init__(self, config_obj):
        self.cfg = config_obj
        self.session = self.cfg.SESSION_CLASS()
        self.state = dict.fromkeys((
            '__EVENTVALIDATION',
            '__VIEWSTATE',
            '__EVENTTARGET',
            '__EVENTARGUMENT',
            ))
        self.logger = logging.getLogger('legistar')

    def sleep(self):
        if self.SLEEP:
            time.sleep(random.randint(50, 200) / 100.0)

    def check_resp(self, resp):
        if resp.status_code != 200:
            msg = 'Error fetching page [%d]: %s'
            args = (resp.status_code, resp.text)
            self.critical(msg, *args)
            raise Exception(msg % args)

    def update_state(self, resp):
        doc = lxml.html.fromstring(resp.text)
        form = dict(doc.forms[0].fields)
        for key in self.state.keys() & form.keys():
            self.state[key] = form.get(key)

    def get(self, url, **kwargs):
        _kwargs = dict(self.cfg.requests_kwargs)
        _kwargs.update(kwargs)
        resp = self.session.get(url, **_kwargs)
        self.check_resp(resp)
        self.update_state(resp)
        self.sleep()
        return resp

    def post(self, url, data=None, **kwargs):
        _kwargs = dict(self.cfg.requests_kwargs)
        _kwargs.update(kwargs)
        _data = dict(self.state)

        # We need to include self.state in the post data, but do it first
        # so that passed-in data can overrite state params, like event target.
        if data is not None:
            _data.update(data or {})

        resp = self.session.post(url, _data, **_kwargs)
        self.check_resp(resp)
        self.update_state(resp)
        self.sleep()
        return resp
