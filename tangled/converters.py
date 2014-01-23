from collections import OrderedDict
from functools import partial

from tangled.util import abs_path, load_object


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
    name of a converter in this module without its ``as_`` prefix.

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


def as_abs_path(v):
    v = v.strip()
    if not v:
        return None
    return abs_path(v)


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


def as_args(*converters, item_sep=', '):
    r"""Make a converter that converts lines of args using ``converters``.

    ``None`` can be passed to indicate that an arg doesn't require
    conversion.

    This would typically be used to parse lines of args from a settings
    file::

        [app]
        args = a 1
               b 2

    Which would be translated into something like this, where
    ``my_func`` is the function (or class) you want to pass the args
    to::

        >>> lines = 'a, 1\nb, 2'
        >>> my_converter = as_args(None, 'int')
        >>> my_func = lambda x, y: (x, y)
        >>> for arg_spec in my_converter(lines):
        ...     my_func(*arg_spec['args'], **arg_spec['kwargs'])
        ...
        ('a', 1)
        ('b', 2)

    You can also specify keyword args using tuples of
    ``(name, converter)``::

        >>> my_func = lambda a, b=None: (a, b)
        >>> my_converter = as_args('int', ('b', 'str'))
        >>> my_converter('1, 2')[0]['args'] == [1]
        True
        >>> my_converter('1, 2')[0]['kwargs'] == {'b': '2'}
        True

    """
    def converter(v):
        v = as_seq_of_seq(v, item_sep=item_sep)
        args_list = []
        for line in v:
            args = []
            kwargs = OrderedDict()
            for arg_val, arg_converter in zip(line, converters):
                arg_name = None
                if isinstance(arg_converter, tuple):
                    arg_name, arg_converter = arg_converter
                if arg_converter is not None:
                    arg_converter = get_converter(arg_converter)
                    arg_val = arg_converter(arg_val)
                if arg_name is None:
                    args.append(arg_val)
                else:
                    kwargs[arg_name] = arg_val
            args_list.append({'args': args, 'kwargs': kwargs})
        return args_list
    return converter


# Map builtins to our converters
MAP = {
    'bool': as_bool,
    'list': as_list,
    'object': as_object,
    'tuple': as_tuple,
}
