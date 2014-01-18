from abc import abstractmethod
from collections import MutableMapping, MutableSequence, OrderedDict

from tangled.decorators import reify


class ARegistry(MutableMapping):

    @abstractmethod
    def register(self, key, component, differentiator=None):
        """Register a component."""
        raise NotImplementedError

    @abstractmethod
    def get(self, key, differentiator=None, default=None):
        """Get a component."""
        raise NotImplementedError

    @abstractmethod
    def get_all(self, key, default=None):
        """Get all the components registered by ``key``."""
        raise NotImplementedError

    @abstractmethod
    def remove(self, key, differentiator=None):
        """Remove a component."""
        raise NotImplementedError

    @abstractmethod
    def contains(self, key, differentiator=None):
        raise NotImplementedError

    @abstractmethod
    def has_any(self, key):
        """Are there any components registered under ``key``?

        This looks for ``key`` without considering differentiators.

        This is a companion to :meth:`get_all`. You might use it
        like this::

            if registry.has_any('kale'):
                kale = registry.get_all('kale')

        """
        raise NotImplementedError


class Registry(ARegistry):

    """A component registry."""

    @reify
    def _components(self):
        # key => {differentiator => component}
        return OrderedDict()

    def register(self, key, component, differentiator=None, replace=False):
        if key not in self._components:
            self._components[key] = OrderedDict()
        components = self._components[key]
        if differentiator in components and not replace:
            existing_component = components[differentiator]
            raise KeyError(
                '[{}, {}] already present in registry as {}. Use replace=True '
                'if you really want to replace it.'
                .format(key, differentiator, existing_component))
        components[differentiator] = component

    def get(self, key, differentiator=None, default=None):
        # The super version of get() calls our __getitem__(); if our
        # __getitem__() raises a KeyError, the default is returned.
        return super(MutableMapping, self).get([key, differentiator], default)

    def get_required(self, key, differentiator=None):
        return self[[key, differentiator]]

    def get_all(self, key, default=None, as_dict=False):
        """Return all components for ``key`` in registration order."""
        if key in self._components:
            components = self._components[key]
        else:
            return default
        if as_dict:
            return components
        else:
            return list(components.values())

    def remove(self, key, differentiator=None):
        del self._components[key][differentiator]

    def contains(self, key, differentiator=None):
        _components = self._components
        return key in _components and differentiator in _components[key]

    def has_any(self, key):
        return key in self._components

    # MutableMapping interface. Keys must be either a hashable object
    # (as usual) or a two-element list of [key, differentiator]. In the
    # former case, the differentiator will be automatically set to None.
    # In the latter case, a list is required because a list can't be
    # used as a dictionary key (so we avoid clashes where a key is
    # passed as a tuple without a differentiator).

    @staticmethod
    def _get_key_and_differentiator(key):
        if isinstance(key, MutableSequence):
            key, differentiator = key
        else:
            differentiator = None
        return key, differentiator

    def __setitem__(self, key, component):
        key, differentiator = self._get_key_and_differentiator(key)
        self.register(key, component, differentiator)

    def __getitem__(self, key):
        key, differentiator = self._get_key_and_differentiator(key)
        if not self.contains(key, differentiator):
            raise KeyError([key, differentiator])
        return self._components[key][differentiator]

    def __delitem__(self, key):
        key, differentiator = self._get_key_and_differentiator(key)
        self.remove(key, differentiator)

    def __iter__(self):
        _components = self._components
        for key in _components:
            for differentiator in _components[key]:
                yield [key, differentiator]

    def __len__(self):
        num_components = 0
        for key in self._components:
            num_components += len(self._components[key])
        return num_components

    def __hash__(self):
        return object.__hash__(self)

    def __repr__(self):
        r = []
        for (key, differentiator), component in self.items():
            r.append('{}, {}: {}'.format(key, differentiator, component))
        return '\n'.join(r)


process_registry = Registry()
process_registry.register(ARegistry, Registry)
