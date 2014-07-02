import os
from fnmatch import fnmatchcase


ALWAYS_EXCLUDE = [
    # generic
    '*__pycache__*',
    'build', 'build.*',
    'dist', 'dist.*',
    'docs', 'docs.*',
    # buildout
    'bin', 'bin.*',
    'develop-eggs', 'develop-eggs.*',
    'parts', 'parts.*',
]


def find_packages(where='.', include=('*',), exclude=()):
    """Return a list of packages under the specified path.

    ``where`` is the relative or absolute path to the root directory
    containing packages--i.e., it's the top level source directory.

    ``include`` is a list of *package* names to include. This can
    contain shell style wild cards patterns. The default is to include
    all packages under ``where``.

    ``exclude`` is a list of package names to exclude.

    To be included in the package list, a package must be both included
    and *not* excluded. Exclusions have precedence over inclusions.

    In addition, several directories will never be considered packages
    (e.g., build, docs); see :global:`ALWAYS_EXCLUDE` for the complete
    list.

    TODO: If a package is in the include list, include it even if it's
          in the `ALWAYS_EXCLUDE` list.

    """
    packages = []
    where = os.path.normpath(os.path.abspath(where))
    include = _make_package_filter(include)
    exclude = _make_package_filter(list(exclude) + ALWAYS_EXCLUDE)
    for current_dir, *_ in os.walk(where):
        rel_path = os.path.relpath(current_dir, where)
        if '.' not in rel_path:
            pkg_name = '.'.join(rel_path.split(os.path.sep))
            if include(pkg_name) and not exclude(pkg_name):
                packages.append(pkg_name)
    return packages


def _make_package_filter(patterns):
    return lambda pkg_name: any(fnmatchcase(pkg_name, p) for p in patterns)
