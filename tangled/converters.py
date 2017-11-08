import inspect
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

    If ``converter`` is not a string, it will be returned as is, except
    in the special case of ``None``, which will cause the identity
    function to be returned.

    Otherwise, ``converter`` can be any builtin name (some of which are
    handled specially), the name of a converter in this module, or the
    name of a converter in this module without its ``as_`` prefix.

    """
    if converter is None:
        return as_self
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


def as_self(v):
    return v


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

    If ``v`` isn't a string, it will be converted to the specified
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


def as_seq_of_seq(sep='\n', type_=list, item_sep=None, line_type=tuple,
                  item_converter=None):
    """Make a converter that converts a str to a sequence of sequences.

    Typically, this is used to convert lines containing items separated
    by spaces (e.g., as might be found in an INI file).

    If an ``item_converter`` is specified, each line item will be
    converted accordingly.

    E.g.::

        >>> s = '''
        ... 1 2 3
        ... a b c
        ... '''
        >>> as_seq_of_seq()(s)
        [('1', '2', '3'), ('a', 'b', 'c')]
        >>> as_seq_of_seq()('')
        []
        >>> as_seq_of_seq(sep=';', item_sep=',')('1, 2; 3, 4')
        [('1', '2'), ('3', '4')]
        >>> c = as_seq_of_seq(sep=';', item_sep=',', item_converter=int)
        >>> c('1, 2; 3, 4')
        [(1, 2), (3, 4)]

    """
    if item_converter is not None:
        item_converter = get_converter(item_converter)

    def converter(v):
        if not v.strip():
            return type_()
        # split input string into lines
        lines = as_tuple(v, sep)
        # split each line into a sequence of items
        lines = (as_tuple(line, item_sep) for line in lines)
        # convert line items
        if item_converter is not None:
            new_lines = []
            for line in lines:
                new_line = tuple(item_converter(i) for i in line)
                new_lines.append(new_line)
            lines = new_lines
        # convert each of the sequences to the requested type
        lines = type_(line_type(line) for line in lines)
        return lines

    return converter


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


def as_func_args(func, converters={}, item_sep=', ', _skip_first=False):
    r"""Make a converter that converts lines of args based on ``func``.

    This inspects ``func`` and configures converters based on the types
    of its args as follows:

        - If an arg has no default, no converter will be used unless
          a converter is specified for it via ``converters``
        - If an arg has a default that's a built-in type, the
          corresponding converter will be used unless a different
          converter is specified via ``converters``
        - If an arg has a default that's *not* a built-in type, that
          type will be used as the converter unless a different
          converter is specified via ``converters``

    The resulting converter would typically be used to parse lines of
    args from a settings file.

    Examples::

        >>> lines = ('1, 1, 1, 1\n1, 0, 1, 1')
        >>> c = as_func_args((lambda a, b=True, i=1, s='s': None), converters={'a': int})
        >>> args_list = c(lines)
        >>> args = args_list[0]
        >>> args['a']
        1
        >>> args['b']
        True
        >>> args['i']
        1
        >>> args['s']
        '1'
        >>> args = args_list[1]
        >>> args['b']
        False
        >>> c = as_func_args(as_func_args, converters={'func': 'object'})
        >>> args = c('tangled.converters:as_func_args')[0]
        >>> args['func'].__name__
        'as_func_args'

    """
    func = load_object(func)
    signature = inspect.signature(func)
    parameters = iter(signature.parameters.values())
    if _skip_first:
        next(parameters)

    arg_converters = OrderedDict()
    for i, p in enumerate(parameters):
        name = p.name
        if name in converters:
            converter = converters[name]
        elif name is None:
            # Positional-only arg
            name = (None, i)
            converter = 'self'
        elif p.default is p.empty:
            converter = 'self'
        elif p.default is None:
            converter = 'self'
        else:
            c = p.default.__class__
            is_builtin = c is __builtins__.get(c.__name__)
            converter = c.__name__ if is_builtin else c
        arg_converters[name] = get_converter(converter)

    line_splitter = as_seq_of_seq(item_sep=item_sep)

    def converter(lines):
        lines = line_splitter(lines)
        args_list = []
        for line in lines:
            args = OrderedDict()
            for v, name in zip(line, arg_converters):
                converter = arg_converters[name]
                args[name] = converter(v)
            args_list.append(args)
        return args_list

    return converter


as_meth_args = partial(as_func_args, _skip_first=True)


def as_args(*converters, item_sep=', '):
    r"""Make a converter that converts lines of args using ``converters``.

    ``None`` or ``'self'`` can be passed to indicate that an arg doesn't
    require conversion.

    This would typically be used to parse lines of args from a settings
    file::

        [app]
        args = a 1
               b 2

    Which would be translated into something like this, where
    ``my_func`` is the function (or class) you want to pass the args
    to::

        >>> lines = 'a, 1\nb, 2'
        >>> my_converter = as_args('self', 'int')
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
    converters = [_normalize_converter(c) for c in converters]
    line_splitter = as_seq_of_seq(item_sep=item_sep)

    def converter(lines):
        lines = line_splitter(lines)
        args_list = []
        for line in lines:
            args, kwargs = [], OrderedDict()
            for arg_val, arg_converter in zip(line, converters):
                arg_name, arg_converter = arg_converter
                arg_val = arg_converter(arg_val)
                if arg_name is None:
                    args.append(arg_val)
                else:
                    kwargs[arg_name] = arg_val
            args_list.append({'args': args, 'kwargs': kwargs})
        return args_list

    return converter


def _normalize_converter(converter):
    if isinstance(converter, (list, tuple)):
        name, converter = converter
        return name, get_converter(converter)
    else:
        return None, get_converter(converter)


# Map builtins to our converters
MAP = {
    'bool': as_bool,
    'list': as_list,
    'object': as_object,
    'tuple': as_tuple,
}
