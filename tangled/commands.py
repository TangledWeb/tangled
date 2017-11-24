from runcommands import command
from runcommands.command import Command
from runcommands.commands import local
from runcommands.util import get_all_list


@command
def build_docs(config, overwrite=False, source='docs', destinaton='docs/_build'):
    local(config, ('sphinx-build', '-E' if overwrite else '', source, destinaton))


__all__ = get_all_list(vars())
