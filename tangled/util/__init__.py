import importlib
import inspect

from . import path, random
from .path import *
from .random import *


__all__ = [
    'NOT_SET',
    'BOOL_STR_MAP',
    'STR_BOOL_MAP',
    'as_bool',
    'filter_items',
    'get_items_with_key_prefix',
    'load_object',
] + path.__all__ + random.__all__


NOT_SET = type('NOT_SET', (), {
    '__bool__': (lambda self: False),
    '__str__': (lambda self: 'NOT_SET'),
    '__repr__': (lambda self: 'NOT_SET'),
    '__copy__': (lambda self: self),
})()
"""A ``None``-ish constant for use where ``None`` may be a valid value."""


BOOL_STR_MAP = {
    True: ('true', 'yes', 'y', 'on', '1'),
    False: ('false', 'no', 'n', 'off', '0'),
}


STR_BOOL_MAP = {}
for b, strs in BOOL_STR_MAP.items():
    for s in strs:
        STR_BOOL_MAP[s] = b


def as_bool(value):
    """Convert value to bool."""
    if isinstance(value, str):
        try:
            return STR_BOOL_MAP[value.strip().lower()]
        except KeyError:
            raise ValueError('Could not convert {} to bool'.format(value))
    return bool(value)


def filter_items(items,
                 include=lambda k, v: True,
                 exclude=lambda k, v: False,
                 processors=()):
    """Filter and optionally process ``items``; yield pairs.

    ``items`` can be any object with a ``.items()`` method that returns
    a sequence of pairs (e.g., a dict), or it can be a sequence of pairs
    (e.g., a list of 2-item tuples).

    Each item will be passed to ``include`` and then to ``exclude``;
    they must return ``True`` and ``False`` respectively for the item to
    be yielded.

    If there are any ``processors``, each included item will be passed
    to each processor in turn.

    """
    try:
        items = items.items()
    except AttributeError:
        pass
    for k, v in items:
        if include(k, v) and not exclude(k, v):
            for processor in processors:
                k, v = processor(k, v)
            yield k, v


def get_items_with_key_prefix(items, prefix, strip_prefix=True, processors=()):
    """Filter ``items`` to those with a key that starts with ``prefix``.

    ``items`` is typically a dict but can also be a sequence. See
    :func:`filter_items` for more on that.

    """
    include = lambda k, v: k.startswith(prefix)
    if strip_prefix:
        prefix_len = len(prefix)
        processors = (lambda k, v: (k[prefix_len:], v),) + processors
    filtered = filter_items(items, include=include, processors=processors)
    return items.__class__(filtered)


def load_object(obj, obj_name=None, package=None, level=2):
    """Load an object.

    ``obj`` may be an object or a string that points to an object. If
    it's a string, the object will be loaded and returned from the
    specified path. If it's any other type of object, it will be
    returned as is.

    The format of a path string is either 'package.module' to load a
    module or 'package.module:object' to load an object from a module.

    The object name can be passed via ``obj_name`` instead of in the
    path (if the name is passed both ways, the name in the path will
    win).

    Examples::

        >>> load_object('tangled.util:load_object')
        <function load_object at ...>
        >>> load_object('tangled.util', 'load_object')
        <function load_object at ...>
        >>> load_object('tangled.util:load_object', 'IGNORED')
        <function load_object at ...>
        >>> load_object('.util:load_object', package='tangled')
        <function load_object at ...>
        >>> load_object('.:load_object', package='tangled.util')
        <function load_object at ...>
        >>> load_object(':load_object', package='tangled.util')
        <function load_object at ...>
        >>> load_object(load_object)
        <function load_object at ...>
        >>> load_object(load_object, 'IGNORED', 'IGNORED', 'IGNORED')
        <function load_object at ...>

    """
    if isinstance(obj, str):
        if is_object_path(obj):
            module_name, obj_name = obj.split(':')
            if not module_name:
                module_name = '.'
        elif is_module_path(obj):
            module_name = obj
        else:
            raise ValueError('Path is not an object or module path: %s' % obj)
        if module_name.startswith('.') and package is None:
            package = caller_package(level)
        obj = importlib.import_module(module_name, package)
        if obj_name:
            attrs = obj_name.split('.')
            for attr in attrs:
                obj = getattr(obj, attr)
    return obj


def caller_package(level=2):
    frame = inspect.stack()[level][0]
    package = frame.f_globals['__package__']
    return package
