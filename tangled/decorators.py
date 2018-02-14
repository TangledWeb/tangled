import functools
import pkgutil
import sys
import threading

from tangled.util import fully_qualified_name, load_object


class cached_property:

    """Similar to @property but caches value on first access.

    When a cached property is first accessed, its value will be computed
    and cached in the instance's ``__dict__``. Subsequent accesses will
    retrieve the cached value from the instance's ``__dict__``.

    .. note:: :meth:`__get__` will always be called to retrieve the
        cached value since this is a so-called "data descriptor". This
        *might* be a performance issue in some scenarios due to extra
        lookups and method calls. To bypass the descriptor in cases
        where this might be a concern, one option is to store the cached
        value in a local variable.

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
        self.lock = threading.Lock()

    def __call__(self, fget):
        self._set_fget(fget)
        return self

    def __get__(self, obj, cls=None):
        if obj is None:  # property accessed via class
            return self
        name, attrs = self.__name__, obj.__dict__
        if name not in attrs:
            # Make other threads wait while the cached value is being
            # computed due to attribute access. If some other thread is
            # already computing the cached value, wait here until it's
            # set.
            with self.lock:
                # This extra check is here in case a thread set the
                # cached value while other threads were waiting.
                if name not in attrs:
                    self._add_to_dependency_map(obj, name)
                    attrs[name] = self.fget(obj)
                    attrs[self._was_set_directly_name(obj, name)] = False
        return attrs[name]

    def __set__(self, obj, value):
        self._update(obj, value)

    def __delete__(self, obj):
        self._update(obj)

    def _set_fget(self, fget):
        self.fget = fget
        self.__name__ = fget.__name__
        self.__doc__ = fget.__doc__

    def _update(self, obj, *args):
        name, attrs = self.__name__, obj.__dict__
        with self.lock:
            if name not in attrs:
                self._add_to_dependency_map(obj, name)

            if args:
                attrs[name] = args[0]
                was_set_directly = True
            else:
                if name in attrs:
                    del attrs[name]
                was_set_directly = False

            attrs[self._was_set_directly_name(obj, name)] = was_set_directly
            self._reset_dependents(obj)

    def _was_set_directly_name(self, obj, name):
        cls_name = self.__class__.__name__
        obj_cls_name = obj.__class__.__name__
        return '_%s__%s_%s_was_set_directly' % (obj_cls_name, name, cls_name)

    def _add_to_dependency_map(self, obj, name):
        if self.dependencies:
            dependency_map = self._get_dependency_map(obj)
            dependency_map[name] = self.dependencies

    def _dependency_map_name(self, obj):
        cls_name = self.__class__.__name__
        obj_cls_name = obj.__class__.__name__
        return '_%s__%s_dependency_map' % (obj_cls_name, cls_name)

    def _get_dependency_map(self, obj):
        obj_cls = obj.__class__
        dependency_map_name = self._dependency_map_name(obj)
        if not hasattr(obj_cls, dependency_map_name):
            setattr(obj_cls, dependency_map_name, {})
        dependency_map = getattr(obj_cls, dependency_map_name)
        return dependency_map

    def _reset_dependents(self, obj):
        """Reset cached properties that depend on this property.

        When this property is set or deleted, this finds its dependent
        cached properties and deletes them so that their values will be
        recomputed on next access. Properties that were set directly
        will be skipped.

        """
        name, attrs = self.__name__, obj.__dict__
        dependency_map = self._get_dependency_map(obj)
        was_set_directly_name = self._was_set_directly_name

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
    def reset_dependents_of(cls, obj, name, *, _lock=threading.Lock(), _fake_props={}):
        """Reset dependents of ``obj.name``.

        This is intended for use in overridden ``__setattr__`` and
        ``__delattr__`` methods for resetting cached properties that are
        dependent on regular attributes.

        """
        if isinstance(getattr(obj.__class__, name, None), cls):
            return

        key = obj.__class__, name

        # Ensure only one thread attempts to creates the fake property.
        with _lock:
            if key not in _fake_props:
                fake_fget = lambda self: None
                fake_fget.__name__ = name
                _fake_props[key] = cls(fake_fget)

        fake_prop = _fake_props[key]

        with fake_prop.lock:
            fake_prop._reset_dependents(obj)


def per_instance_lru_cache(maxsize=128, typed=False):
    """Least-recently-used cache decorator for methods and properties.

    This is based on :func:`functools.lru_cache` in the Python standard
    library and mimics its API and behavior. The major difference is
    that this decorator creates a per-instance cache for the decorated
    method instead of a cache shared by all instances.

    When :func:`functools.lru_cache` is used on a method, the cache for
    the method is shared between *all* instances. This means that
    clearing the LRU cache for a method clears it for all instances and
    that hit/miss info is an aggregate of calls from all instances.

    This is intended for use with instance methods and properties. For
    class and static methods, :func:`functools.lru_cache` should work
    fine, since the issues noted above aren't applicable.

    As with :func:`functools.lru_cache`, the arguments passed to wrapped
    methods must be hashable.

    Args:
        maxsize (int):
            - If positive, LRU-caching will be enabled and the cache
              can grow up to the specified size, after which the least
              recently used item will be dropped.
            - If ``None``, the LRU functionality will be disabled and
              the cache can grow without bound.
            - If 0, caching will be disabled and this will effectively
              just keep track of how many times a method is called per
              instance.
            - A negative value is effectively the same as passing 1.

        typed (bool): Whether arguments with different types will be
            cached separately. E.g., 1 and 1.0 both hash to 1, so
            ``self.method(1)`` and ``self.method(1.0)`` will result in
            the same key being generated by default.

    Example::

        >>> class C:
        ...
        ...     @per_instance_lru_cache()
        ...     def some_method(self, x, y, z):
        ...         return x + y + z
        ...
        ...     @property
        ...     @per_instance_lru_cache(1)
        ...     def some_property(self):
        ...         result = 2 ** 1000000
        ...         return result

        >>> c = C()
        >>> c.some_method(1, 2, 3)
        6
        >>> C.some_method.cache_info(c)
        CacheInfo(hits=0, misses=1, maxsize=128, currsize=1)
        >>> c.some_method(1, 2, 3)
        6
        >>> C.some_method.cache_info(c)
        CacheInfo(hits=1, misses=1, maxsize=128, currsize=1)

        >>> d = C()
        >>> d.some_method(1, 2, 3)
        6
        >>> d.some_method(4, 5, 6)
        15
        >>> d.some_method(4, 5, 6)
        15
        >>> C.some_method.cache_info(d)
        CacheInfo(hits=1, misses=2, maxsize=128, currsize=2)
        >>> C.some_method.cache_clear(d)
        >>> C.some_method.cache_info(d)
        CacheInfo(hits=0, misses=0, maxsize=128, currsize=0)

        >>> C.some_method.cache_info(c)  # Unaffected by instance d
        CacheInfo(hits=1, misses=1, maxsize=128, currsize=1)

        >>> c.some_property  # doctest: +ELLIPSIS
        9900...
        >>> C.some_property.fget.cache_info(c)
        CacheInfo(hits=0, misses=1, maxsize=1, currsize=1)
        >>> c.some_property  # doctest: +ELLIPSIS
        9900...
        >>> C.some_property.fget.cache_info(c)
        CacheInfo(hits=1, misses=1, maxsize=1, currsize=1)

    """
    if maxsize is not None and not isinstance(maxsize, int):
        raise TypeError('Expected maxsize to be an integer or None')

    def decorator(method):
        instance_wrappers = {}
        get_instance_wrapper = instance_wrappers.get
        lock = threading.Lock()
        lru_cache = functools.lru_cache

        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            with lock:
                # The ID of the instance is explicitly used as the key
                # into the instance wrapper dict to ensure a cache is
                # created per instance even if instance.__hash__() is
                # overridden. This also avoids reentrancy issues since
                # this will keep instance.__eq__() from being called
                # when looking up the key.
                key = id(self)
                instance_wrapper = get_instance_wrapper(key)
                if instance_wrapper is None:
                    instance_wrapper = lru_cache(maxsize, typed)(method)
                    instance_wrappers[key] = instance_wrapper
            result = instance_wrapper(self, *args, **kwargs)
            return result

        def cache_info(instance):
            with lock:
                instance_wrapper = get_instance_wrapper(id(instance))
                if instance_wrapper is not None:
                    return instance_wrapper.cache_info()
                return functools._CacheInfo(0, 0, maxsize, 0)

        def cache_clear(instance):
            with lock:
                instance_wrapper = get_instance_wrapper(id(instance))
                if instance_wrapper is not None:
                    return instance_wrapper.cache_clear()

        wrapper.__wrapped__ = method
        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return wrapper

    return decorator


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
