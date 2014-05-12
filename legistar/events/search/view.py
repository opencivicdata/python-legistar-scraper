from legistar.base.view import View
from legistar.base.form import Form
import legistar.events.search.table
import legistar.events.search.form


class SearchView(View):
    TableClass = 'legistar.events.search.table.Table'
    FormClass = 'legistar.events.search.form.Form'

    def get_query(self, time_period=None, bodies=None):
        time_period = time_period or self.cfg.EVENTS_DEFAULT_TIME_PERIOD
        bodies = bodies or self.cfg.EVENTS_DEFAULT_BODIES
        query = {
            self.cfg.EVENTS_BODIES_EL_NAME: bodies,
            self.cfg.EVENTS_TIME_PERIOD_EL_NAME: time_period,
            }
        return query