import builtins
import configparser
import json
import os

from tangled.util import (
    abs_path, get_items_with_key_prefix, is_asset_path, is_object_path, load_object)


def parse_settings_file(path, section='app', interpolation=None, meta_settings=True, **kwargs):
    """Parse settings from the .ini file at ``path``.

    ``path`` can be a file system path or an asset path. ``section``
    specifies which [section] to get settings from.

    By default, some extra metadata will be added to the settings parsed
    from a file. These are the file name the settings were loaded from
    (__file__), the base file names of any extended files (__base__ and
    __bases__), and the environment indicated by the file's base name
    (env). Use ``meta_settings=False`` to disable this.

    ``kwargs`` are the keyword args for :func:`parse_settings`.

    """
    file_name = abs_path(path)
    file_dir = os.path.dirname(file_name)
    defaults = {'__dir__': json.dumps(file_dir)}
    if interpolation is None:
        interpolation = configparser.ExtendedInterpolation()
    parser = configparser.ConfigParser(
        defaults=defaults, delimiters='=', interpolation=interpolation)

    with open(file_name) as fp:
        parser.read_file(fp)

    try:
        settings = dict(parser[section])
    except KeyError:
        raise ValueError('Settings file has no [{}] section'.format(section))

    try:
        settings = parse_settings(settings, **kwargs)
    except ValueError as exc:
        file_name = os.path.relpath(file_name, os.getcwd())
        message = '{exc} in {file_name}'.format_map(locals())
        raise ValueError(message) from None

    required = kwargs.pop('required', None)

    if meta_settings:
        settings['__file__'] = file_name
        settings['__base__'] = None
        settings['__bases__'] = ()
        if 'env' not in settings:
            env = os.path.basename(file_name)
            env = os.path.splitext(env)[0]
            settings['env'] = env

    extends = settings.pop('extends', None)
    if extends:
        if not is_asset_path(extends):
            extends = os.path.join(file_dir, extends)
        base_file_name = abs_path(extends)
        base_settings = parse_settings_file(
            base_file_name, section, interpolation, meta_settings, **kwargs)
        if meta_settings:
            settings['__base__'] = base_file_name
            settings['__bases__'] = (base_file_name,)
            settings['__bases__'] += base_settings['__bases__']
        base_settings.update(settings)
        settings = base_settings

    if required:
        check_required(settings, required)

    return settings


def parse_settings(settings, defaults={}, required=(), extra={}, prefix=None, strip_prefix=True):
    """Convert settings values.

    All settings values should be JSON-encoded strings. For example::

        debug = true
        factory:object = "tangled.web:Application"
        something:package.module:SomeClass = "value"

    Settings passed via ``defaults`` will be added if they're not
    already present in ``settings``.

    To convert only a subset of the settings, pass ``prefix``; only the
    settings with a key matching ``prefix`` will be returned (see
    :func:`get_items_with_key_prefix` for details).

    Required fields can be listed in ``required``. If any required
    fields are missing, a ``ValueError`` will be raised.

    For each setting:

        - If the key specifies a type using ``key:type`` syntax, the
          specified type will be used to parse the value. The type can
          refer to any callable that accepts a single string.

          If the type is specified as ``object``, :func:`.load_object()`
          will be used to parse the value.

          The ``:type`` will be stripped from the key.

        - Otherwise, the value will be passed to ``json.loads()``.

    The original ``settings`` dict will not be modified.

    """
    loads = json.loads
    parsed_settings = {}
    parsed_settings.update(defaults)

    if prefix is not None:
        settings = get_items_with_key_prefix(settings, prefix, strip_prefix)

    for key, value in settings.items():
        value = value.strip()
        if not value:
            value = None
        else:
            key, *rest = key.split(':', 1)
            try:
                value = loads(value)
            except ValueError:
                message = 'Could not parse JSON value for {key}'.format(key=key)
                raise ValueError(message) from None
            if rest:
                kind = get_type(rest[0])
                value = kind(value)
        parsed_settings[key] = value

    parsed_settings.update(extra)

    if required:
        check_required(parsed_settings, required)

    return parsed_settings


def check_required(settings, required):
    """Ensure ``settings`` contains the ``required`` keys."""
    missing = []
    for r in required:
        if r not in settings:
            missing.append(r)
    if missing:
        raise ValueError(
            'Missing required settings: {}'.format(', '.join(missing)))


def get_type(name: str):
    """Get the type corresponding to ``name``."""
    if name is None:
        return str
    if name == 'object':
        return load_object
    if hasattr(builtins, name):
        return getattr(builtins, name)
    if is_object_path(name):
        return load_object(name)
    raise TypeError('Unknown type: %s' % name)
