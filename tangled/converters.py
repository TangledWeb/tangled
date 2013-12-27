from functools import partial

from tangled.util import load_object


BOOL_STR_MAP = {
    True: ('true', 'yes', 'y', 'on', '1'),
    False: ('false', 'no', 'n', 'off', '0'),
}


STR_BOOL_MAP = {}
for b, strs in BOOL_STR_MAP.items():
    for s in strs:
        STR_BOOL_MAP[s] = b


def get_converter(converter):
    """Given a ``converter`` name, return the actual converter.

    If ``converter`` is not a string, it will be returned as is.

    Otherwise, ``converter`` can be any builtin name (some of which are
    handled specially), the name of a converter in this module, or the
    name of a converter in this module without its 'as_' prefix.

    """
    if not isinstance(converter, str):
        return converter
    converters = {k: v for k, v in globals().items() if k.startswith('as_')}
    as_name = 'as_{}'.format(converter)
    if converter in MAP:
        # builtins that need special treatment (e.g., bool)
        converter = MAP[converter]
    elif converter in __builtins__:
        # builtins that don't need special treatment (e.g., int)
        converter = __builtins__[converter]
    elif converter in converters:
        converter = converters[converter]
    elif as_name in converters:
        converter = converters[as_name]
    else:
        raise TypeError('Unknown converter: {}'.format(converter))
    return converter


def as_object(v):
    v = v.strip()
    if not v:
        return None
    return load_object(v)


def as_bool(v):
    if isinstance(v, str):
        try:
            return STR_BOOL_MAP[v.strip().lower()]
        except KeyError:
            raise ValueError('Could not convert {} to bool'.format(v))
    else:
        return bool(v)


def as_seq(v, sep=None, type_=tuple):
    """Convert a string to a sequence.

    If ``v`` isn't a string, it will converted to the specified
    ``type_``.

    Examples::

        >>> as_seq('a')
        ('a',)
        >>> as_seq('a b c')
        ('a', 'b', 'c')
        >>> as_seq('a', sep=',')
        ('a',)
        >>> as_seq('a,', sep=',')
        ('a',)
        >>> as_seq('a, b', sep=',')
        ('a', 'b')
        >>> as_seq('a b c', type_=list)
        ['a', 'b', 'c']
        >>> as_seq(('a', 'b'))
        ('a', 'b')
        >>> as_seq(('a', 'b'), type_=list)
        ['a', 'b']

    """
    if isinstance(v, str):
        v = v.strip()
        v = v.strip(sep)
        v = type_(i.strip() for i in v.split(sep))
    if not isinstance(v, type_):
        v = type_(v)
    return v


as_list = partial(as_seq, type_=list)
as_tuple = partial(as_seq, type_=tuple)


def as_seq_of(item_converter, sep=None, type_=tuple, args=(), kwargs=None):
    """Create a sequence, converting each item with ``item_converter``."""
    item_converter = get_converter(item_converter)
    def converter(v):
        items = as_tuple(v, sep)
        return type_(
            item_converter(item, *args, **(kwargs or {})) for item in items)
    return converter


as_list_of = partial(as_seq_of, type_=list)
as_tuple_of = partial(as_seq_of, type_=tuple)
as_list_of_objects = as_seq_of(load_object, type_=list)


def as_seq_of_seq(v, sep='\n', type_=list, item_sep=None, line_type=tuple):
    """Convert ``v`` to a list of tuples.

    E.g.::

        >>> s = '''
        ... 1 2 3
        ... a b c
        ... '''
        >>> as_seq_of_seq(s)
        [('1', '2', '3'), ('a', 'b', 'c')]
        >>> as_seq_of_seq('')
        []

    """
    if not v.strip():
        return type_()
    # split input string into lines
    lines = as_tuple(v, sep)
    # split each line into a sequence of items
    lines = (as_tuple(line, item_sep) for line in lines)
    # convert each of the sequences to the requested type
    lines = type_(line_type(line) for line in lines)
    return lines


def as_first_of(a_converter, *converters):
    """Try each converter in ``converters``."""
    converters = (a_converter,) + converters
    def converter(v):
        for c in converters:
            c = get_converter(c)
            try:
                return c(v)
            except ValueError:
                pass
        raise TypeError('Could not convert {}'.format(v))
    return converter


# Map builtins to our converters
MAP = {
    'bool': as_bool,
    'list': as_list,
    'object': as_object,
    'tuple': as_tuple,
}
