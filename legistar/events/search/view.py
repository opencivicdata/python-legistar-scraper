from legistar.base.form import Form
from legistar.base.searchview import SearchView


class SearchView(SearchView):
    PUPATYPE = 'events'
    VIEWTYPE = 'search'
    sources_note = 'Events search'
