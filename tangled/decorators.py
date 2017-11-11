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
        self.dependencies = set(dependencies) if dependencies else None

    def __call__(self, fget):
        self._set_fget(fget)
        return self

    def __get__(self, obj, cls=None):
        if obj is None:  # property accessed via class
            return self
        name, attrs = self.__name__, obj.__dict__
        if name not in attrs:
            self._add_to_dependency_map(obj, name)
            attrs[name] = self.fget(obj)
            attrs[self._was_set_directly_name(obj, name)] = False
        return attrs[name]

    def __set__(self, obj, value):
        name, attrs = self.__name__, obj.__dict__
        if name not in attrs:
            self._add_to_dependency_map(obj, name)
        attrs[name] = value
        attrs[self._was_set_directly_name(obj, name)] = True
        self._reset_dependents(obj)

    def __delete__(self, obj):
        name, attrs = self.__name__, obj.__dict__
        if name not in attrs:
            self._add_to_dependency_map(obj, name)
        else:
            del attrs[name]
            self._reset_dependents(obj)
        attrs[self._was_set_directly_name(obj, name)] = False

    def _set_fget(self, fget):
        self.fget = fget
        self.__name__ = fget.__name__
        self.__doc__ = fget.__doc__

    def _add_to_dependency_map(self, obj, name):
        if self.dependencies:
            dependency_map = self.get_dependency_map(obj)
            dependency_map[name] = self.dependencies

    def _reset_dependents(self, obj):
        # When this property is set or deleted, find its dependent
        # cached properties and delete them so that their values will be
        # recomputed on next access. Properties that were set directly
        # will be skipped.
        self.reset_dependents_of(obj, self.__name__, regular=False)

    @classmethod
    def get_dependency_map(cls, obj):
        obj_cls = obj.__class__
        dependency_map_name = cls._dependency_map_name(obj)
        if not hasattr(obj_cls, dependency_map_name):
            setattr(obj_cls, dependency_map_name, {})
        dependency_map = getattr(obj_cls, dependency_map_name)
        return dependency_map

    @classmethod
    def reset_dependents_of(cls, obj, name, *, regular=True):
        """Reset cached properties that depend on ``obj.name``.

        In the case where ``name`` refers to a regular attribute instead
        of a cached property, this has to be called from an overridden
        ``__setattr__`` or ``__delattr__`` in the class ``obj`` is an
        instance of.

        """
        # Skip resetting dependents if the named attribute is a cached
        # property but regular attribute handling was requested. This is
        # a hack for classes that override __setattr__ and __delattr__
        # so they don't need to check if a cached property is being
        # updated. The reason for all this is to avoid resetting
        # dependents twice for cached properties.
        if regular and isinstance(getattr(obj.__class__, name, None), cls):
            return

        attrs = obj.__dict__
        dependency_map = cls.get_dependency_map(obj)
        was_set_directly_name = cls._was_set_directly_name

        # For each cached property that has dependencies...
        for dependent, dependencies in dependency_map.items():
            reset = (
                # Is the updated property one of its dependencies?
                name in dependencies and
                # Is the attribute set on the instance?
                dependent in attrs and
                # Was it set directly via `self.x = y`? If so, don't
                # reset it.
                not attrs.get(was_set_directly_name(obj, dependent))
            )
            if reset:
                delattr(obj, dependent)

    @classmethod
    def _dependency_map_name(cls, obj):
        return '_%s__%s_dependency_map' % (obj.__class__.__name__, cls.__name__)

    @classmethod
    def _was_set_directly_name(cls, obj, name):
        return '_%s__%s_%s_was_set_directly' % (obj.__class__.__name__, name, cls.__name__)


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
