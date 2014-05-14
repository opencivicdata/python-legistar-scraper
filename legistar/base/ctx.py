import collections
import lxml.html
from hercules import CachedAttr, DictSetDefault


class CtxValue:
    '''Wrapped values get lookup in the ancestor ChainMap objects. Setting
    this attributes sets the value in the instance's own ChainMap.
    '''
    def __init__(self, key):
        self.key = key

    def __get__(self, inst, owner=None):
        self.on_get(inst, owner)
        val = inst.ctx.get(self.key)
        if val is None and hasattr(self, 'get_value'):
            val = self.get_value(inst, owner)
            inst.ctx[self.key] = val
        return val

    def __set__(self, inst, value):
        self.on_set(inst, value)
        inst.ctx[self.key] = value

    def on_get(self, inst, owner):
        pass

    def on_set(self, inst, value):
        pass


class Doc(CtxValue):
    '''This one's expensive, so fetch it lazily and cache it.
    '''
    def get_value(self, inst, owner):
        # Blab.
        msg_args = (inst, inst.url)
        inst.debug('%s is fetching %s', *msg_args)

        # Fetch the page, parse.
        resp = inst.cfg.client.get(inst.url)
        doc = lxml.html.fromstring(resp.text)
        doc.make_links_absolute(inst.url)

        # Cache it and blab some more.
        inst.ctx['doc'] = doc
        inst.debug('%s cached parsed lxml doc %s', *msg_args)
        return doc

    def add_to_sources(self, inst, *args):
        with DictSetDefault(inst.ctx, 'sources', {}) as sources:
            sources[inst.sources_note] = inst.url

    # Add the url to sources when this doc gets used.
    on_get = on_set = add_to_sources


class CtxMixin:
    '''Lookups for these attributes on mixed objects will fail over
    to whatever object's ChainMap the object's own ChainMap was derived
    from, and on up the chain, all the way back the jursdiction's config
    obj.
    '''
    url = CtxValue('url')
    doc = Doc('doc')
    client = CtxValue('client')
    config = config_obj = cfg = CtxValue('config')

    info = CtxValue('info')
    debug = CtxValue('debug')
    warn = warning = CtxValue('warning')
    critical = CtxValue('critical')
    error = CtxValue('error')

    @property
    def ctx(self):
        ctx = getattr(self, '_ctx', None)
        if ctx is not None:
            return ctx
        else:
            ctx = collections.ChainMap()
            self._ctx = ctx
            return ctx

    @ctx.setter
    def ctx(self, ctx):
        self._ctx = ctx

    def set_parent_ctx(self, ctx):
        self.ctx = collections.ChainMap(self.ctx.maps[0], *ctx.maps)

    def provide_ctx_to(self, has_child_ctx):
        '''Set self's ctx as the parent of child's ctx.
        '''
        has_child_ctx.set_parent_ctx(self.ctx)
        return has_child_ctx

    def inherit_ctx_from(self, has_parent_ctx):
        '''Set this object as the ctx parent of has_child_ctx.
        '''
        self.set_parent_ctx(has_parent_ctx.ctx)
        return has_parent_ctx

    def make_child(self, child_type, *child_args, **child_kwargs):
        child = child_type(*child_args, **child_kwargs)
        return self.provide_ctx_to(child)