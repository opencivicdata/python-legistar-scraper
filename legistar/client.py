import logging
import lxml.html


class Client:

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

    def update_state(self, resp):
        doc = lxml.html.fromstring(resp.text)
        form = dict(doc.forms[0].fields)
        for key in tuple(self.state.keys()):
            self.state[key] = form.get(key)

    def get(self, url, **kwargs):
        _kwargs = dict(self.cfg.requests_kwargs)
        _kwargs.update(kwargs)
        resp = self.session.get(url, **kwargs)
        self.update_state(resp)
        return resp

    def post(self, url, data=None, **kwargs):
        _kwargs = dict(self.cfg.requests_kwargs)
        _kwargs.update(kwargs)
        resp = self.session.post(url, data, **kwargs)
        self.update_state(resp)
        return resp
