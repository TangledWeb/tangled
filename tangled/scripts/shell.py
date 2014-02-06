import code
import sys

from tangled.abcs import ACommand
from tangled.util import load_object


def strip_lower(val):
    return val.strip().lower()


def local_type(val):
    k, v = val.split('=')
    v = load_object(v)
    return k, v


class ShellCommand(ACommand):

    # In order of preference
    shells = ['bpython', 'ipython', 'python']

    @classmethod
    def configure(cls, parser):
        parser.add_argument(
            '--shell', type=strip_lower, choices=cls.shells, default=None)
        parser.add_argument(
            'locals', nargs='*', type=local_type,
            help='Pass additional shell locals using '
                 'name=package.module:object syntax')

    def run(self):
        shell_locals = self.get_locals()
        if self.args.locals:
            shell_locals.update(self.args.locals)

        banner = ['Tangled Shell']
        if shell_locals:
            banner.append('Locals:')
            for k, v in shell_locals.items():
                v = str(v)
                v = v.replace('\n', '\n       ' + ' ' * len(k))
                banner.append('    {} = {}'.format(k, v))
        banner = '\n'.join(banner)

        def try_shells(shells):
            for shell in shells:
                success = getattr(self, shell)(shell_locals, banner)
                if success:
                    return shell

        if self.args.shell:
            if not try_shells([self.args.shell]):
                alt_shells = self.shells[:]
                alt_shells.remove(self.args.shell)
                self.print_error(
                    '{} shell not available; trying others ({})'
                    .format(self.args.shell, ', '.join(alt_shells)))
                try_shells(alt_shells)
        else:
            try_shells(self.shells)

    def get_locals(self):
        return {}

    def bpython(self, shell_locals, banner):
        try:
            import bpython
            from bpython import embed
        except ImportError:
            return False
        banner = 'bpython {}\n{}'.format(bpython.__version__, banner)
        embed(locals_=shell_locals, banner=banner)
        return True

    def ipython(self, shell_locals, banner):
        try:
            from IPython.terminal.embed import InteractiveShellEmbed
        except ImportError:
            return False
        InteractiveShellEmbed(user_ns=shell_locals, banner2=banner)()
        return True

    def python(self, shell_locals, banner):
        banner = 'python {}\n{}'.format(sys.version, banner)
        code.interact(banner=banner, local=shell_locals)
        return True
