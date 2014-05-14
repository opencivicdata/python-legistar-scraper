import pytest

from legistar.base.ctx import CtxMixin


class A(CtxMixin):
    pass


class TestCtxMixin:

    def test_inherit_ctx(self):
        parent = A()
        child = A()

        assert parent.ctx is not child.ctx

        parent.ctx['a'] = 1
        assert 'a' not in child.ctx

        child.inherit_ctx_from(parent)
        assert 'a' in child.ctx

    def test_provide_ctx(self):
        parent = A()
        child = A()

        assert parent.ctx is not child.ctx
        parent.ctx['a'] = 1
        assert 'a' not in child.ctx
        parent.provide_ctx_to(child)
        assert 'a' in child.ctx

    def test_doc_attr(self):
        parent = A()
        child = A()

        # Attr is not set.
        assert child.doc is None
        assert parent.doc is None
        assert 'doc' not in parent.ctx
        assert 'doc' not in child.ctx

        # Set it on the parent.
        parent.doc = 'somedoc'
        child.inherit_ctx_from(parent)
        assert 'doc' in parent.ctx
        assert 'doc' in child.ctx
        assert parent.doc is child.doc

        # Set child to something else.
        child.doc = 'someotherdoc'
        assert parent.doc is not child.doc


    def test_url_attr(self):
        parent = A()
        child = A()

        # Attr is not set.
        assert child.url is None
        assert parent.url is None
        assert 'url' not in parent.ctx
        assert 'url' not in child.ctx

        # Set it on the parent.
        parent.url = 'somedoc'
        child.inherit_ctx_from(parent)
        assert 'url' in parent.ctx
        assert 'url' in child.ctx
        assert parent.url is child.url

        # Set child to something else.
        child.url = 'someotherdoc'
        assert parent.url is not child.url


    def test_config_attr(self):
        parent = A()
        child = A()

        # Attr is not set.
        assert child.config is None
        assert parent.config is None
        assert 'config' not in parent.ctx
        assert 'config' not in child.ctx

        # Set it on the parent.
        parent.config = 'somedoc'
        child.inherit_ctx_from(parent)
        assert 'config' in parent.ctx
        assert 'config' in child.ctx
        assert parent.config is child.config

        # Set child to something else.
        child.config = 'someotherdoc'
        assert parent.config is not child.config
