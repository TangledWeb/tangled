"""Abstract base classes."""
import sys
from abc import ABCMeta, abstractmethod


class ACommand(metaclass=ABCMeta):

    """Abstract base class for tangled commands."""

    def __init__(self, parser, args):
        self.parser = parser
        self.args = args

    @classmethod
    @abstractmethod
    def configure(cls, parser):
        raise NotImplementedError()

    @abstractmethod
    def run(self):
        raise NotImplementedError()

    def print_error(self, *args, file=sys.stderr, **kwargs):
        print(*args, file=file, **kwargs)
