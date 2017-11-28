import argparse
import pkg_resources
import sys

from .abcs import ACommand
from .registry import process_registry


def main(argv=None):
    """Entry point for running a tangled command.

    Such commands are registered via the ``tangled.scripts`` entry
    point like so::

        [tangled.scripts]
        mycommand = mypackage.mymodule:MyCommand

    The command can be run as ``tangled mycommand ...``.

    """
    parser = argparse.ArgumentParser(
        description='Run a tangled command',
    )

    subparsers = parser.add_subparsers(title='Subcommands')

    # Load subcommands from entry points
    # Command can also be added directly to the process registry
    entry_points = pkg_resources.iter_entry_points('tangled.scripts')
    for entry_point in entry_points:
        name = entry_point.name
        if not entry_point.attrs:
            entry_point.attrs = ('Command',)
        subparser = subparsers.add_parser(name)
        subparser.set_defaults(command_name=name)
        Command = entry_point.load()
        Command.configure(subparser)
        process_registry.register(ACommand, Command, name)

    args = parser.parse_args(argv)

    if hasattr(args, 'command_name'):
        command_type = process_registry.get(ACommand, args.command_name)
        command = command_type(parser, args)
        return command.run()
    else:
        parser.print_help()
        return -1


if __name__ == '__main__':
    return_code = main()
    sys.exit(return_code)
