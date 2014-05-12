
class View:
    '''Base class for Legistar views. Pass in a config_obj and
    either url or parse lxml.html doc.

    Each view has an associated top-level FormClass and TableClass
    that are used to submit the View's form and extract information.
    Those related classes as specificed in the jurisdiction's
    legistar.jxn_config.Config object, or in the default Config object.
    '''
    def __init__(self, config_obj, url=None, doc=None):
        self.url = url
        self.doc = doc
        self.config_obj = config_obj

    # ------------------------------------------------------------------------
    # Managed attributes
    # ------------------------------------------------------------------------
    @property
    def url(self):
        '''self.url either returns the url or falls back to the
        jurisdiction's root url.
        '''
        if self._url is None:
            return self.cfg.root_url
        else:
            return self._url

    @url.setter
    def url(self, url):
        self._url = url

    @property
    def doc(self):
        '''self.doc fetches and parsed the html document with lxml.
        '''
        if self._doc is None:
            resp = self.cfg.client.get(self.url)
            doc = lxml.html.fromstring(resp.text)
            doc.make_links_absolute(self.url)
            self._doc = doc
        else:
            doc = self._doc
        return doc

    @doc.setter
    def doc(self, doc):
        self._doc = doc

    @property
    def config_obj(self):
        return self._config_obj

    @config_obj.setter
    def config_obj(self, config_obj):
        '''Config obj needs to be instantiated for descriptors to work.
        '''
        if isinstance(config_obj, type):
            self._config_obj = config_obj()
        else:
            self._config_obj = config_obj

    cfg = config_obj

    # ------------------------------------------------------------------------
    # Access to configable properties.
    # ------------------------------------------------------------------------
    @property
    def viewmeta(self):
        '''Return the view metadata for this View based on its PUPATYPE.
        '''
        return self.cfg.viewmeta[self.PUPATYPE]

    @property
    def viewtype_meta(self):
        '''Return the viewtype metadata for this View based on its PUPATYPE
        and its VIEWTYPE, which is either 'search' or 'detail'.
        '''
        return getattr(self.viewmeta, self.VIEWTYPE)

    # ------------------------------------------------------------------------
    # View interface.
    # ------------------------------------------------------------------------
    def __iter__(self):
        for result_page in self._gen_search_results():
            for obj in result_page:
                yield obj

    def _gen_search_results(self):
        Form = self.viewtype_meta.Form
        yield from Form(self)