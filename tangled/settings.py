import configparser
import os

from tangled import converters
from tangled.util import abs_path, get_items_with_key_prefix


def parse_settings(settings, conversion_map={}, defaults={}, required=(),
                   prefix=None, strip_prefix=True, processors=()):
    """Convert the values of ``settings``.

    To convert only a subset of the settings, pass ``prefix``; only the
    settings with a key matching ``prefix`` will be returned (see
    :func:`get_items_with_key_prefix` for details).

    Settings passed via ``defaults`` will be added if they're not
    already present in ``settings`` (and they'll be converted too).

    Required fields can be listed in ``required``. If any required
    fields are missing, a ``ValueError`` will be raised.

    For each setting...

        - If the key for the setting specifies a converter via the
          `key:converter` syntax, the specified function will be called
          to convert its value (the function must be a builtin or a
          function from :mod:`tangled.converters`).

        - If the key for the setting is in ``conversion_map``, the
          function it maps to will be used to convert its value.

        - If the special key '*' is in ``conversion_map``, the function
          it maps to will be used to convert the setting.

        - Otherwise, the value will be used as is (i.e., as a string).

    The original ``settings`` dict will not be changed.

    """
    parsed_settings = {}
    if prefix is not None:
        settings = get_items_with_key_prefix(
            settings, prefix, strip_prefix, processors)
    for k, v in defaults.items():
        settings.setdefault(k, v)
    for k, v in settings.items():
        if isinstance(v, str):
            if ':' in k:
                k, converter = k.split(':')
                converter = converters.get_converter(converter)
            elif k in conversion_map:
                converter = converters.get_converter(conversion_map[k])
            elif '*' in conversion_map:
                converter = converters.get_converter(conversion_map['*'])
            else:
                converter = lambda v: v
            v = converter(v)
        parsed_settings[k] = v
    if required:
        _check_required(parsed_settings, required)
    return parsed_settings


def parse_settings_file(path, section='app', meta_settings=True, **kwargs):
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
    defaults = {'__here__': os.path.dirname(file_name)}
    parser = configparser.ConfigParser(delimiters='=', defaults=defaults)

    with open(file_name) as fp:
        parser.read_file(fp)

    try:
        settings = dict(parser[section])
    except KeyError:
        raise ValueError('Settings file has no [{}] section'.format(section))

    settings = parse_settings(settings, **kwargs)
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
        base_file_name = abs_path(extends)
        base_settings = parse_settings_file(
            base_file_name, section, meta_settings, **kwargs)
        if meta_settings:
            settings['__base__'] = base_file_name
            settings['__bases__'] = (base_file_name,)
            settings['__bases__'] += base_settings['__bases__']
        base_settings.update(settings)
        settings = base_settings

    if required:
        _check_required(required)

    return settings


def _check_required(settings, required):
    missing = []
    for r in required:
        if r not in settings:
            missing.append(r)
    if missing:
        raise ValueError(
            'Missing required settings: {}'.format(', '.join(missing)))
