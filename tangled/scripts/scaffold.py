import os
import pkg_resources
import shutil
import string
import tempfile
from datetime import datetime

from tangled.abcs import ACommand
from tangled.util import asset_path


BUILDOUT_TEMPLATE = """\
[buildout]
parts = dev
newest = false
develop = .
          ../tangled
          ../tangled.web

[dev]
recipe = zc.recipe.egg
eggs = ${package_name}
dependent-scripts = true
interpreter = python

"""


class ScaffoldCommand(ACommand):

    @classmethod
    def configure(cls, parser):
        parser.add_argument('scaffold')
        parser.add_argument('package_name')
        parser.add_argument('-d', '--output-dir', default=None)
        parser.add_argument('--overwrite', action='store_true', default=False)
        parser.add_argument('--buildout', action='store_true', default=False)
        parser.add_argument('--dry-run', action='store_true', default=False)
        parser.add_argument('--author', default=os.environ.get('USER', ''))

    def run(self, **extra_template_vars):
        args = self.args
        package_name = args.package_name

        if args.dry_run:
            temp_output_dir = output_dir = tempfile.mkdtemp()
        else:
            output_dir = args.output_dir
            if output_dir is None:
                output_dir = os.path.join(os.getcwd(), package_name)

        relative_package_dir = package_name.replace('.', os.path.sep)
        package_dir = os.path.join(output_dir, relative_package_dir)

        if os.path.exists(output_dir):
            if args.overwrite:
                print('Overwriting {}'.format(output_dir))
                shutil.rmtree(output_dir)
            else:
                self.print_error('{} exists; use --overwrite to replace'.format(output_dir))
                return 1

        scaffold_dir = self._get_scaffold_dir(args.scaffold)
        if scaffold_dir is None:
            self.print_error('Unknown scaffold: {}'.format(args.scaffold))
            return 1

        print('Using {0.scaffold} scaffold'.format(args))
        print('Creating package at {}'.format(output_dir))

        if args.dry_run:
            print('\n\n\n')

        scaffold_package_dir = os.path.join(output_dir, '__package__')

        tangled_version = pkg_resources.get_distribution('tangled').version
        template_vars = {
            'package': package_name.split('.')[-1],
            'package_name': package_name,
            'package_dir': package_dir,
            'relative_package_dir': relative_package_dir,
            'author': args.author,
            'year': datetime.today().year,
            'version_tangled': tangled_version,
            'version_tangled_web': tangled_version,
        }
        template_vars.update(extra_template_vars)

        # Copy the scaffold to the output directory
        shutil.copytree(scaffold_dir, output_dir)
        # Create the package directory structure
        os.makedirs(package_dir)
        # Remove the leaf package directory
        shutil.rmtree(package_dir)
        # Copy the scaffold's __package__ directory to where the leaf was
        shutil.move(scaffold_package_dir, package_dir)

        if args.buildout:
            with open(os.path.join(output_dir, 'buildout.cfg'), 'w') as fp:
                fp.write(BUILDOUT_TEMPLATE)

        for current_dir, sub_dirs, files in os.walk(output_dir):
            for d in sub_dirs:
                if d == '__pycache__':
                    shutil.rmtree(os.path.join(current_dir, d))
                    self.print_error(
                        'Removed __pycache__ directory from {}'
                        .format(current_dir))
            for f in files:
                f = os.path.join(current_dir, f)
                with open(f) as fp:
                    content = fp.read()
                template = string.Template(content)
                content = template.substitute(template_vars)
                if args.dry_run:
                    rel_path = os.path.relpath(f, output_dir)
                    print(
                        '# {}\n{}\n\n\n'
                        .format(rel_path, content or '# Empty file'))
                else:
                    os.remove(f)
                    if f.endswith('.py.template'):
                        f = f.rsplit('.', 1)[0]
                    with open(f, 'w') as fp:
                        fp.write(content)

        if args.dry_run:
            shutil.rmtree(temp_output_dir)

    def _get_scaffold_dir(self, scaffold_name):
        if ':' not in scaffold_name:
            entry_points = pkg_resources.iter_entry_points('tangled.scaffolds')
            for entry_point in entry_points:
                if entry_point.name == scaffold_name:
                    module_name = entry_point.module_name
                    path = entry_point.attrs[0]
                    return asset_path(module_name, path)
            else:
                return None
        return asset_path(scaffold_name)
