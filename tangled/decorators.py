class reify:

    """Like @property but "freezes" attribute on first access."""

    def __init__(self, fget):
        self.fget = fget
        self.__name__ = fget.__name__
        self.__doc__ = fget.__doc__

    def __get__(self, obj, cls=None):
        if obj is None:  # property accessed via class
            return self
        value = self.fget(obj)
        setattr(obj, self.fget.__name__, value)
        return value


class cached_property:

    """Like @property but caches value on first access.

    This can be useful for cases where you might want to unset
    (i.e., ``del``) a value so that it's reinitialized on the next
    access.

    It's okay to ``del`` a cached property that hasn't been accessed
    yet--doing so is a no-op.

    """

    def __init__(self, fget):
        self.fget = fget
        self.__name__ = fget.__name__
        self.__doc__ = fget.__doc__

    def __get__(self, obj, cls=None):
        if obj is None:  # property accessed via class
            return self
        if self.__name__ not in obj.__dict__:
            obj.__dict__[self.__name__] = self.fget(obj)
        return obj.__dict__[self.__name__]

    def __set__(self, obj, value):
        obj.__dict__[self.__name__] = value

    def __delete__(self, obj):
        if self.__name__ in obj.__dict__:
            del obj.__dict__[self.__name__]
