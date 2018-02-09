import binascii
import hmac
import os
import random
import string


__all__ = ['constant_time_compare', 'random_bytes', 'random_string']


random = random.SystemRandom()


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
