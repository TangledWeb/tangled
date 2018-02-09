import importlib
import inspect
import os


__all__ = [
    'abs_path',
    'asset_path',
    'fully_qualified_name',
    'is_asset_path',
    'is_module_path',
    'is_object_path',
]


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
    if inspect.ismodule(obj):
        return obj.__name__
    return '{}.{}'.format(obj.__module__, obj.__qualname__)


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
