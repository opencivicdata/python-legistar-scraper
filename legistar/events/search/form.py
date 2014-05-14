from legistar.base.form import Form


class Form(Form):
    '''Model the legistar "Calendar" search form.
    '''
    sources_note = 'Events search'

    def get_query(self, time_period=None, bodies=None):
        time_period = time_period or self.cfg.EVENTS_DEFAULT_TIME_PERIOD
        bodies = bodies or self.cfg.EVENTS_DEFAULT_BODIES
        query = {
            self.cfg.EVENTS_BODIES_EL_NAME: bodies,
            self.cfg.EVENTS_TIME_PERIOD_EL_NAME: time_period,
            }
        return query