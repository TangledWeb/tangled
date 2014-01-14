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

    def exit(self, message=None, status=1):
        """Exit with error code by default.

        If ``message`` is passed, it will be printed to stderr.

        """
        if message:
            if status == 0:
                print(message)
            else:
                self.print_error(message)
        sys.exit(status)
