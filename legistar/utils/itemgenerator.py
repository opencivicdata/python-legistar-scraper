import inspect
import functools


class SkipItem(Exception):
    '''Methods decorated with @make_item can throw this exception
    to prevent the function's output from being collected by the
    iterator.
    '''


def make_item(key, wrapwith=None):
    '''Decorator used to mark instance methods as producing a key, value
    item 2-tuple.

    If the key is dot-qualified, the decorator registers the
    function on the instance's jurisdiction object. The function
    will get invoked later by the itemgenerator subtype in the
    approriate context.
    '''

    pupatype = None
    if '.' in key:
        corrected_pupatype = dict(
            person='people',
            organization='orgs',
            org='orgs',
            bill='bills',
            event='events',
            vote='votes')
        pupatype, key = key.split('.')
        pupatype = corrected_pupatype.get(pupatype, pupatype)

    def decorator(f):
        itemdata = dict(key=key, wrapwith=wrapwith)
        f._itemdata = itemdata
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            # Call the wrapped func.
            result = f(*args, **kwargs)
            # Apply any requested type conversion.
            if wrapwith is not None:
                result = wrapwith(result)
            return key, result

        if pupatype:
            # The jurisdiction metaclass collects these on each instance.
            wrapped._is_aggregator_func = True
            wrapped._pupatype = pupatype

        return wrapped
    return decorator


class ItemGeneratorHelper:

    SkipItem = SkipItem

    def __init__(self, inst):
        self.inst = inst
        self.iter_init()

    def __iter__(self):
        self.iter_init()
        return self

    def iter_init(self):
        self.itemgen = self.gen_items(self.inst)

    def __next__(self):
        return next(self.itemgen)

    def gen_items(self, inst):
        for name, member in inspect.getmembers(inst):
            itemdata = getattr(member, '_itemdata', None)
            if itemdata is None:
                continue
            try:
                result = self.invoke_method(name, member, inst)
            except self.SkipItem:
                continue
            yield result

    def invoke_method(self, name, method, inst):
        invoke_method = getattr(inst, 'invoke_method', None)
        if invoke_method is not None:
            return invoke_method(name, member, inst)
        args = getattr(inst, 'args', ())
        kwargs = getattr(inst, 'kwargs', {})
        return method(*args, **kwargs)


class ItemGenerator:

    SkipItem = SkipItem

    def __init__(self):
        self.iter_init()

    def __iter__(self):
        self.iter_init()
        return self

    def iter_init(self):
        self.itemgen = ItemGeneratorHelper(self)

    def __next__(self):
        return next(self.itemgen)


def gen_items(inst):
    yield from ItemGeneratorHelper(inst)

