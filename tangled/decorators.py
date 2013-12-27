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
        self.values = {}
        self.__name__ = fget.__name__
        self.__doc__ = fget.__doc__

    def __get__(self, obj, cls=None):
        if obj is None:  # property accessed via class
            return self
        obj_id = id(obj)
        if obj_id not in self.values:
            self.values[obj_id] = self.fget(obj)
        return self.values[obj_id]

    def __set__(self, obj, value):
        self.values[id(obj)] = value

    def __delete__(self, obj):
        obj_id = id(obj)
        if obj_id in self.values:
            del self.values[obj_id]
