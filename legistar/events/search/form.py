import json

from legistar.base.form import Form


class Form(Form):
    '''Model the legistar "Calendar" search form.
    '''
    sources_note = 'Events search'

    def get_query(self, time_period=None, bodies=None):
        time_period = time_period or self.cfg.EVENTS_SEARCH_TIME_PERIOD
        bodies = bodies or self.cfg.EVENTS_SEARCH_BODIES
        clientstate = json.dumps({'value': time_period})

        query = {
            self.cfg.EVENTS_SEARCH_BODIES_EL_NAME: bodies,
            self.cfg.EVENTS_SEARCH_TIME_PERIOD_EL_NAME: time_period,
            self.cfg.EVENTS_SEARCH_CLIENTSTATE_EL_NAME: clientstate,
            }
        self.debug('Query is %r' % query)
        query = dict(self.client.state, **query)
        return query
