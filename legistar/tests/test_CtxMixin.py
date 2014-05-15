import pytest

from legistar.base.chainmap import CtxMixin


class A(CtxMixin):
    pass


class TestCtxMixin:

    def test_inherit_chainmap(self):
        parent = A()
        child = A()

        assert parent.chainmap is not child.chainmap

        parent.chainmap['a'] = 1
        assert 'a' not in child.chainmap

        child.inherit_chainmap_from(parent)
        assert 'a' in child.chainmap

    def test_provide_chainmap(self):
        parent = A()
        child = A()

        assert parent.chainmap is not child.chainmap
        parent.chainmap['a'] = 1
        assert 'a' not in child.chainmap
        parent.provide_chainmap_to(child)
        assert 'a' in child.chainmap

    def test_doc_attr(self):
        parent = A()
        child = A()

        # Attr is not set.
        assert child.doc is None
        assert parent.doc is None
        assert 'doc' not in parent.chainmap
        assert 'doc' not in child.chainmap

        # Set it on the parent.
        parent.doc = 'somedoc'
        child.inherit_chainmap_from(parent)
        assert 'doc' in parent.chainmap
        assert 'doc' in child.chainmap
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
        assert 'url' not in parent.chainmap
        assert 'url' not in child.chainmap

        # Set it on the parent.
        parent.url = 'somedoc'
        child.inherit_chainmap_from(parent)
        assert 'url' in parent.chainmap
        assert 'url' in child.chainmap
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
        assert 'config' not in parent.chainmap
        assert 'config' not in child.chainmap

        # Set it on the parent.
        parent.config = 'somedoc'
        child.inherit_chainmap_from(parent)
        assert 'config' in parent.chainmap
        assert 'config' in child.chainmap
        assert parent.config is child.config

        # Set child to something else.
        child.config = 'someotherdoc'
        assert parent.config is not child.config
