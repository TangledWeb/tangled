import pkgutil
import sys

from tangled.util import fully_qualified_name, load_object


class cached_property:

    """Similar to @property but caches value on first access.

    When the property is first accessed, its value is computed and set
    as an instance attribute (i.e., in the instance's ``__dict__``).
    Subsequent accesses will get the value directly from the instance's
    ``__dict__`` (i.e., this descriptor will not be invoked).

    The property can be set and deleted as usual. When the property is
    deleted, its value will be recomputed and re-set on the next access.

    """

    def __init__(self, fget):
        self.fget = fget
        self.__name__ = fget.__name__
        self.__doc__ = fget.__doc__

    def __get__(self, obj, cls=None):
        if obj is None:  # property accessed via class
            return self
        obj.__dict__[self.__name__] = self.fget(obj)
        return obj.__dict__[self.__name__]


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
