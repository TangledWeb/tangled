import pkgutil
import sys

from tangled.util import fully_qualified_name, load_object


class cached_property:

    """Similar to @property but caches value on first access.

    When a cached property is first accessed, its value will be computed
    and cached in the instance's ``__dict__``. Subsequent accesses will
    retrieve the cached value from the instance's ``__dict__``.

    The property can be set and deleted as usual. When the property is
    deleted, its value will be recomputed and reset on the next access.

    It's safe to ``del`` a property that hasn't been set--this won't
    raise an attribute error as might be expected since a cached
    property can't really be deleted (since it will be recomputed the
    next time it's accessed).

    A cached property can specify its dependencies (other cached
    properties) so that when its dependencies are set or deleted, the
    cached property will be cleared and recomputed on next access::

        >>> class T:
        ...
        ...     @cached_property
        ...     def a(self):
        ...         return 'a'
        ...
        ...     @cached_property('a')
        ...     def b(self):
        ...         return '%s + b' % self.a
        ...
        ...
        >>> t = T()
        >>> t.a
        'a'
        >>> t.b
        'a + b'
        >>> t.a = 'A'
        >>> t.b
        'A + b'

    When a property has been set directly (as opposed to via access), it
    won't be reset when its dependencies are set or deleted. If the
    property is later cleared, it will then be recomputed::

        >>> t = T()
        >>> t.b = 'B'  # set t.b directly
        >>> t.b
        'B'
        >>> t.a = 'A'
        >>> t.b  # t.b was set directly, so setting t.a doesn't affect it
        'B'
        >>> del t.b
        >>> t.b  # t.b was cleared, so it's computed from t.a
        'A + b'

    """

    def __init__(self, *args):
        if args and callable(args[0]):
            self._set_fget(args[0])
            dependencies = args[1:]
        else:
            dependencies = args
        self.dependencies = set(dependencies)

    def __call__(self, fget):
        self._set_fget(fget)
        return self

    def __get__(self, obj, cls=None):
        if obj is None:  # property accessed via class
            return self
        if self.__name__ not in obj.__dict__:
            obj.__dict__[self.__name__] = self.fget(obj)
            obj.__dict__[self.set_directly_name] = False
        return obj.__dict__[self.__name__]

    def __set__(self, obj, value):
        obj.__dict__[self.__name__] = value
        self._del_dependents(obj)
        obj.__dict__[self.set_directly_name] = True

    def __delete__(self, obj):
        if self.__name__ in obj.__dict__:
            del obj.__dict__[self.__name__]
            self._del_dependents(obj)
        obj.__dict__[self.set_directly_name] = False

    def _set_fget(self, fget):
        self.fget = fget
        self.set_directly_name = self._set_directly_name(fget.__name__)
        self.__name__ = fget.__name__
        self.__doc__ = fget.__doc__

    def _set_directly_name(self, name):
        return '__%s_set_directly__' % name

    def _del_dependents(self, obj):
        # When this property is set or deleted, find its dependent
        # cached properties and delete them so that their values will be
        # recomputed on next access. Properties that were set directly
        # will be skipped.
        for name in dir(obj.__class__):
            if name == self.__name__:
                continue
            attr = getattr(obj.__class__, name)
            delete = (
                # Is the attribute a cached property? If not, skip it.
                isinstance(attr, self.__class__) and
                # Is the updated property one of its dependencies?
                self.__name__ in attr.dependencies and
                # Is the attribute set on the instance?
                name in obj.__dict__ and
                # Was it set directly via `self.x = y`? If so, skip it.
                not obj.__dict__.get(self._set_directly_name(name))
            )
            if delete:
                delattr(obj, name)


_ACTION_REGISTRY = {}


def register_action(wrapped, action, tag=None, _registry=_ACTION_REGISTRY):
    """Register a deferred decorator action.

    The action will be performed later when :func:`fire_actions` is
    called with the specified ``tag``.

    This is used like so::

        # mymodule.py

        def my_decorator(wrapped):
            def action(some_arg):
                # do something with some_arg
            register_action(wrapped, action, tag='x')
            return wrapped  # <-- IMPORTANT

        @my_decorator
        def my_func():
            # do some stuff

    Later, :func:`fire_actions` can be called to run ``action``::

        fire_actions(mymodule, tags='x', args=('some arg'))

    """
    _registry.setdefault(tag, {})
    fq_name = fully_qualified_name(wrapped)
    actions = _registry[tag].setdefault(fq_name, [])
    actions.append(action)


def fire_actions(where, tags=(), args=(), kwargs=None,
                 _registry=_ACTION_REGISTRY):
    """Fire actions previously registered via :func:`register_action`.

    ``where`` is typically a package or module. Only actions registered
    in that package or module will be fired.

    ``where`` can also be some other type of object, such as a class, in
    which case only the actions registered on the class and its methods
    will be fired. Currently, this is considered non-standard usage, but
    it's useful for testing.

    If no ``tags`` are specified, all registered actions under ``where``
    will be fired.

    ``*args`` and ``**kwargs`` will be passed to each action that is
    fired.

    """
    where = load_object(where)
    where_fq_name = fully_qualified_name(where)
    tags = (tags,) if isinstance(tags, str) else tags
    kwargs = {} if kwargs is None else kwargs

    if hasattr(where, '__path__'):
        # Load all modules in package
        path = where.__path__
        prefix = where.__name__ + '.'
        for (_, name, is_pkg) in pkgutil.walk_packages(path, prefix):
            if name not in sys.modules:
                __import__(name)

    tags = _registry.keys() if not tags else tags

    for tag in tags:
        tag_actions = _registry[tag]
        for fq_name, wrapped_actions in tag_actions.items():
            if fq_name.startswith(where_fq_name):
                for action in wrapped_actions:
                    action(*args, **kwargs)
