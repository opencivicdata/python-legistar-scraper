import lxml.html
from hercules import DictSetDefault
from legistar.base.ctx import CtxMixin


class View(CtxMixin):
    '''Base class for Legistar views. Pass in a config_obj and
    either url or parse lxml.html doc.

    Each view has an associated top-level FormClass and TableClass
    that are used to submit the View's form and extract information.
    Those related classes as specificed in the jurisdiction's
    legistar.jxn_config.Config object, or in the default Config object.
    '''

    def __init__(self, url=None, doc=None):
        # Setting doc to None forces the view to fetch the page.
        self.ctx['doc'] = doc

        # Allow the url to fall back to the parent ctx url.
        if url is not None:
            self.ctx['url'] = url

    # ------------------------------------------------------------------------
    # Managed attributes
    # ------------------------------------------------------------------------
    @property
    def sources_note(self):
        msg = 'Please set `sources_note` on this class: %r' % self.__class__
        raise NotImplementedError(msg)

    # @property
    # def doc(self):
    #     '''self.doc fetches and parsed the html document with lxml.
    #     '''
    #     if self.ctx['doc'] is None:
    #         resp = self.cfg.client.get(self.url)
    #         doc = lxml.html.fromstring(resp.text)
    #         doc.make_links_absolute(self.url)
    #         self.ctx['doc'] = doc
    #     else:
    #         doc = self.ctx['doc']
    #     with DictSetDefault(self.ctx, 'sources', {}) as sources:
    #         sources[self.sources_note] = self.url
    #     return doc

    # @doc.setter
    # def doc(self, doc):
    #     self.ctx['doc'] = doc

    # ------------------------------------------------------------------------
    # Access to configable properties.
    # ------------------------------------------------------------------------
    @property
    def viewmeta(self):
        '''Return the view metadata for this View based on its PUPATYPE.
        '''
        return self.cfg.viewmeta.get_by_pupatype(self.PUPATYPE)

    @property
    def viewtype_meta(self):
        '''Return the viewtype metadata for this View based on its PUPATYPE
        and its VIEWTYPE, which is either 'search' or 'detail'.
        '''
        return getattr(self.viewmeta, self.VIEWTYPE)
