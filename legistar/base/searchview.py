from legistar.base.view import View


class SearchView(View):

    # ------------------------------------------------------------------------
    # SearchView interface.
    # ------------------------------------------------------------------------
    def __iter__(self):
        '''Iterating over a search view generates tables of paginated search
        results.
        '''
        Form = self.viewtype_meta.Form
        yield from Form(self)