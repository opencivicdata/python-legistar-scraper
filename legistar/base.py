import types
import contextlib
from collections import ChainMap

import lxml.html

from legistar.utils.handythings import (
    CachedAttr, CachedClassAttr, DictSetDefault, NoClobberDict)


class ChainedLookup:
    '''Wrapped values get lookup in the ancestor ChainMap objects. Setting
    this attributes sets the value in the instance's own ChainMap.
    '''
    def __init__(self, key):
        self.key = key

    def __get__(self, inst, owner=None):
        self.on_get(inst, owner)
        val = inst.chainmap.get(self.key)
        if val is None and hasattr(self, 'get_value'):
            val = self.get_value(inst, owner)
            inst.chainmap[self.key] = val
        return val

    def __set__(self, inst, value):
        self.on_set(inst, value)
        inst.chainmap[self.key] = value

    def on_get(self, inst, owner):
        '''Gets called before value is returned.
        '''
        pass

    def on_set(self, inst, value):
        '''Gets called before value is set.
        '''
        pass


class Doc(ChainedLookup):
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
        inst.chainmap['doc'] = doc
        return doc

    def add_to_sources(self, inst, *args):
        '''Add the fetched web page to the parent object's chainmap.
        '''
        with DictSetDefault(inst.chainmap, 'sources', {}) as sources:
            sources[inst.sources_note] = inst.url

    # Add the url to sources when this doc gets used.
    on_get = on_set = add_to_sources


class Base:
    '''Lookups for these attributes on subtypes will fail over
    to whatever object's ChainMap the object's own ChainMap was derived
    from, and on up the chain, all the way back the jursdiction's config
    obj.
    '''
    # The jxn config object.
    config = config_obj = cfg = ChainedLookup('config')
    url = ChainedLookup('url')
    # The lxml.htm doc.
    doc = Doc('doc')
    # The config's requests.Session or Scraper object.
    client = ChainedLookup('client')

    # Logging methods.
    info = ChainedLookup('info')
    debug = ChainedLookup('debug')
    warn = warning = ChainedLookup('warning')
    critical = ChainedLookup('critical')
    error = ChainedLookup('error')

    @property
    def chainmap(self):
        '''This property manages the instance's ChainMap objects.
        '''
        chainmap = getattr(self, '_chainmap', None)
        if chainmap is not None:
            return chainmap
        else:
            chainmap = ChainMap()
            self._chainmap = chainmap
            return chainmap

    @chainmap.setter
    def chainmap(self, chainmap):
        self._chainmap = chainmap

    def set_parent_chainmap(self, chainmap):
        '''Set `chainmap` as the parent of self.chainmap.
        '''
        self.chainmap = ChainMap(self.chainmap.maps[0], *chainmap.maps)

    def provide_chainmap_to(self, has_child_chainmap):
        '''Set self.chainmap as the parent of child's chainmap.
        '''
        has_child_chainmap.set_parent_chainmap(self.chainmap)
        return has_child_chainmap

    def inherit_chainmap_from(self, has_parent_chainmap):
        '''Set this object as the chainmap parent of has_child_chainmap.
        '''
        self.set_parent_chainmap(has_parent_chainmap.chainmap)
        return has_parent_chainmap

    def make_child(self, child_type, *child_args, **child_kwargs):
        '''Invoke the passed in type with the args/kwargs, then provide
        self.chainmap to it, basically making it a child context.
        '''
        child = child_type(*child_args, **child_kwargs)
        return self.provide_chainmap_to(child)


# ----------------------------------------------------------------------------
#  Base Visitor, vendorized from https://github.com/twneale/visitors
# ----------------------------------------------------------------------------
class VisitorContinue(Exception):
    '''If a user-defined visitor function raises this exception,
    children of the visited node won't be visited.
    '''


class VisitorBreak(Exception):
    '''If raised, the visit is immediately done,
    so stop and call finalize.
    '''


class Visitor:
    '''A customizable visitor pattern implementation. Either call
    visitor.visit(thing), which visits `thing` and returns visitor.finalize(),
    or iterate over visitor.itervisit(). Visitor methods can be generators,
    in which case itervisit will yield from each invoked method. Methods
    can also be GeneratorContextManager types, in which case the visit will
    enter the method, continue visiting child nodes, then exit.
    '''
    Continue = VisitorContinue
    Break = VisitorBreak

    # ------------------------------------------------------------------------
    # Define some class level types needed by the internals.
    # ------------------------------------------------------------------------
    GeneratorType = types.GeneratorType
    GeneratorContextManager = contextlib._GeneratorContextManager

    # ------------------------------------------------------------------------
    # Plumbing.
    # ------------------------------------------------------------------------
    @CachedClassAttr
    def _methods(cls):
        return {}

    @CachedClassAttr
    def _method_prefix(cls):
        return getattr(cls, 'method_prefix', 'visit_')

    # ------------------------------------------------------------------------
    # Define the default overridables.
    # ------------------------------------------------------------------------
    def apply_visitor_method(self, method_data, node):
        if hasattr(method_data, '__call__'):
            return method_data(self, node)
        elif isinstance(method_data, tuple):
            method = method_data[0]
            args = method_data[1:]
            return method(self, *args)

    def get_nodekey(self, node):
        '''Given a node, return the string to use in computing the
        matching visitor methodname. Can also be a generator of strings.
        '''
        yield node.__class__.__name__

    def get_children(self, node):
        '''Given a node, return its children.
        '''
        return node.children[:]

    def get_methodnames(self, node):
        '''Given a node, generate all names for matching visitor methods.
        '''
        nodekey = self.get_nodekey(node)
        prefix = self._method_prefix
        if isinstance(nodekey, self.GeneratorType):
            for nodekey in nodekey:
                yield self._method_prefix + nodekey
        else:
            yield self._method_prefix + nodekey

    def get_method(self, node):
        '''Given a particular node, check the visitor instance for methods
        mathing the computed methodnames (the function is a generator).

        Note that methods are cached at the class level.
        '''
        methods = self._methods
        for methodname in self.get_methodnames(node):
            if methodname in methods:
                return methods[methodname]
            else:
                cls = self.__class__
                method = getattr(cls, methodname, None)
                if method is not None:
                    methods[methodname] = method
                    return method

    def get_children(self, node):
        '''Override this to determine how child nodes are accessed.
        '''
        return node.children[:]

    def finalize(self):
        '''Final steps the visitor needs to take, plus the
        return value of .visit, if any.
        '''
        return self

    # ------------------------------------------------------------------------
    # Define the core functionality.
    # ------------------------------------------------------------------------
    def visit(self, node):
        '''The main visit function. Visits the passed-in node and calls
        finalize.
        '''
        tuple(self.itervisit(node))
        result = self.finalize()
        if result is not self:
            return result

    def itervisit(self, node):
        try:
            yield from self.itervisit_nodes(node)
        except self.Break:
            pass

    def itervisit_nodes(self, node):
        try:
            yield from self.itervisit_node(node)
        except self.Continue:
            return
        itervisit_nodes = self.itervisit_nodes
        for child in self.get_children(node):
            yield from itervisit_nodes(child)

    def itervisit_node(self, node):
        '''Given a node, find the matching visitor function (if any) and
        run it. If the result is a context manager, yield from all the nodes
        children before allowing it to exit. Otherwise, return the result.
        '''
        # Get the corresponding method and run it.
        func = self.get_method(node)
        if func is None:
            generic_visit = getattr(self, 'generic_visit', None)
            if generic_visit is not None:
                result = generic_visit(node)
            else:
                # There is no handler defined for this node.
                return
        else:
            result = self.apply_visitor_method(func, node)

        # If result is a generator, yield from it.
        if isinstance(result, self.GeneratorType):
            yield from result

        # If result is a context manager, enter, visit children, then exit.
        elif isinstance(result, self.GeneratorContextManager):
            with result:
                itervisit_nodes = self.itervisit_nodes
                for child in self.get_children(node):
                    try:
                        yield from itervisit_nodes(child)
                    except self.Continue:
                        continue

        # Otherwise just yield the result.
        else:
            yield result

    def visit_node(self, node):
        for result in self.itervisit_node(node):
            return result