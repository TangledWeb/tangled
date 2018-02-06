import binascii
import hmac
import importlib
import inspect
import os
import random
import string
from types import ModuleType


random = random.SystemRandom()


NOT_SET = type('NOT_SET', (), {
    '__bool__': (lambda self: False),
    '__str__': (lambda self: 'NOT_SET'),
    '__repr__': (lambda self: 'NOT_SET'),
    '__copy__': (lambda self: self),
})()
"""A ``None``-ish constant for use where ``None`` may be a valid value."""


def fully_qualified_name(obj):
    """Get the fully qualified name for an object.

    Returns the object's module name joined with its qualified name. If
    the object is a module, its name is returned.

    >>> fully_qualified_name(object)
    'builtins.object'
    >>> import tangled.util
    >>> fully_qualified_name(tangled.util)
    'tangled.util'

    """
    if isinstance(obj, ModuleType):
        return obj.__name__
    return '{}.{}'.format(obj.__module__, obj.__qualname__)


def caller_package(level=2):
    frame = inspect.stack()[level][0]
    package = frame.f_globals['__package__']
    return package


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


def is_asset_path(path) -> bool:
    """Is ``path`` an asset path like ``package.module:path``?

    If ``path`` is absolute, it will not be considered an asset path.
    Otherwise, it will be considered an asset path if it contains a
    colon *and* the module path contains only valid Python identifiers.
    The file system path to the right of the colon can be empty or any
    string (it's ignored here).

    Examples::

        >>> is_asset_path('/some/abs/path')
        False
        >>> is_asset_path('rel/path')
        False
        >>> is_asset_path('package')
        False
        >>> is_asset_path('package:')
        True
        >>> is_asset_path('package.subpackage:rel/path')
        True
        >>> is_asset_path('package.subpackage:')
        True
        >>> is_asset_path('package.subpackage:rel/path')
        True
        >>> is_asset_path('base.ini')
        False

    """
    if os.path.isabs(path) or ':' not in path:
        return False
    module_path, _ = path.split(':', 1)
    return is_module_path(module_path)


def is_module_path(path) -> bool:
    """Is ``path`` a module path like ``package.module``?

    Examples::

        >>> is_module_path('package')
        True
        >>> is_module_path('package.module')
        True
        >>> is_module_path('.module')
        True
        >>> is_module_path('package.module:obj')
        False
        >>> is_module_path('a/b')
        False
        >>> is_module_path('/a/b')
        False

    """
    return all(p.isidentifier() for p in path.lstrip('.').split('.'))


def is_object_path(path) -> bool:
    """Is ``path`` an object path like ``package.module:obj.path``?

    Examples::

        >>> is_object_path('package.module:obj')
        True
        >>> is_object_path('.module:obj')
        True
        >>> is_object_path('package')
        False
        >>> is_object_path('package:')
        False
        >>> is_object_path('a/b')
        False
        >>> is_object_path('/a/b')
        False

    """
    if ':' not in path:
        return False
    pkg_path, *object_path = path.split(':', 1)
    if object_path:
        object_path = object_path[0]
        return is_module_path(pkg_path) and is_module_path(object_path)
    return False


def asset_path(path, *rel_path):
    """Get absolute path to asset in package.

    ``path`` can be just a package name like 'tangled.web' or it can be
    a package name and a relative file system path like
    'tangled.web:some/path'.

    If ``rel_path`` is passed, it will be appended to the base rel. path
    in ``path``.

    Examples::

        >>> asset_path('tangled.util')
        '.../tangled/tangled'
        >>> asset_path('tangled.util:')
        '.../tangled/tangled'
        >>> asset_path('tangled.util:x')
        '.../tangled/tangled/x'
        >>> asset_path('tangled.util', 'x')
        '.../tangled/tangled/x'
        >>> asset_path('tangled.util:x', 'y')
        '.../tangled/tangled/x/y'

    """
    if not (is_asset_path(path) or is_module_path(path)):
        raise ValueError('Path is not an asset path: %s' % path)
    if ':' in path:
        package_name, base_rel_path = path.split(':')
        rel_path = (base_rel_path,) + rel_path
    else:
        package_name = path
    package = importlib.import_module(package_name)
    if not hasattr(package, '__file__'):
        raise ValueError("Can't compute path relative to namespace package")
    package_path = os.path.dirname(package.__file__)
    path = os.path.join(package_path, *rel_path)
    path = os.path.normpath(os.path.abspath(path))
    return path


def abs_path(path):
    """Get abs. path for ``path``.

    ``path`` may be a relative or absolute file system path or an asset
    path. If ``path`` is already an abs. path, it will be returned as
    is. Otherwise, it will be converted into a normalized abs. path.

    """
    if not os.path.isabs(path):
        if is_asset_path(path):
            path = asset_path(path)
        else:
            path = os.path.expanduser(path)
            path = os.path.normpath(os.path.abspath(path))
    return path


BOOL_STR_MAP = {
    True: ('true', 'yes', 'y', 'on', '1'),
    False: ('false', 'no', 'n', 'off', '0'),
}


STR_BOOL_MAP = {}
for b, strs in BOOL_STR_MAP.items():
    for s in strs:
        STR_BOOL_MAP[s] = b


def as_bool(v):
    if isinstance(v, str):
        try:
            return STR_BOOL_MAP[v.strip().lower()]
        except KeyError:
            raise ValueError('Could not convert {} to bool'.format(v))
    return bool(v)


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


ASCII_ALPHANUMERIC = string.ascii_letters + string.digits
BASE64_ALPHABET = ASCII_ALPHANUMERIC + '-_'
HEX = string.digits + 'abcdef'


def random_bytes(n=16, as_hex=True):
    """Return a random string of bytes.

    By default, this will encode 16 random bytes as a 32-character byte
    string of hex digits (i.e., each byte is split into 4 bits and
    encoded as a hex digit).

    In general, whenever ``as_hex`` is True, the number of bytes
    returned will be ``2 * n``.

    >>> len(random_bytes()) == 32
    True
    >>> len(random_bytes(10, as_hex=True)) == 20
    True
    >>> len(random_bytes(7, as_hex=False)) == 7
    True
    >>> random_bytes().__class__ is bytes
    True
    >>> random_bytes(as_hex=False).__class__ is bytes
    True

    """
    _bytes = os.urandom(n)
    if as_hex:
        return binascii.hexlify(_bytes)
    else:
        return _bytes


def random_string(n=32, alphabet=BASE64_ALPHABET, encoding='ascii') -> str:
    """Return a random string with length ``n``.

    By default, the string will contain 32 characters from the URL-safe
    base 64 alphabet.

    ``encoding`` is used only if the ``alphabet`` is a byte string.

    >>> len(random_string()) == 32
    True
    >>> len(random_string(8)) == 8
    True
    >>> len(random_string(7, ASCII_ALPHANUMERIC)) == 7
    True
    >>> random_string().__class__ is str
    True
    >>> random_string(alphabet=HEX).__class__ is str
    True
    >>> 'g' not in random_string(alphabet=HEX)
    True

    """
    a = alphabet[0]
    chars = (random.choice(alphabet) for _ in range(n))
    if isinstance(a, str):
        return ''.join(chars)
    elif isinstance(a, bytes):
        return b''.join(chars).decode(encoding)
    raise TypeError('Expected str or bytes; got %s' % a.__class__)


def constant_time_compare(a, b):
    """Compare two bytes or str objects in constant time.

    ``a`` and ``b`` must be either both bytes OR both strings w/ only
    ASCII chars.

    Returns ``False`` if ``a`` and ``b`` have different lengths, if
    either is a string with non-ASCII characters, or their types don't
    match.

    See :func:`hmac.compare_digest` for more details.

    """
    if len(a) != len(b):
        return False
    try:
        return hmac.compare_digest(a, b)
    except TypeError:
        return False
