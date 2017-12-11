import glob
import os
import posixpath
import shutil
import site
import unittest

from runcommands import command
from runcommands.commands import local, show_config
from runcommands.util import confirm
from runcommands.util import get_all_list


@command
def init(config, overwrite=False):
    virtualenv(config, overwrite=overwrite)
    install(config)
    test(config)


@command
def virtualenv(config, overwrite=False):
    where = '.env'
    if os.path.exists(where):
        if overwrite:
            print('Overwriting', where)
            shutil.rmtree(where)
            create = True
        else:
            print(where, 'exists')
            create = False
    else:
        create = True
    if create:
        local(config, ('virtualenv -p python{python.version}', where))


@command
def install(config, upgrade=False):
    local(config, (
        'pip install',
        '--upgrade' if upgrade else '',
        '-r requirements.txt',
    ))
    site_packages = '.env/lib/python{python.version}/site-packages'.format_map(config)
    site.addsitedir(site_packages)


@command
def test(config, coverage=True, tests=(), verbose=False):
    where = os.path.join(config.cwd, config.package.replace('.', os.sep))
    coverage = coverage and not tests
    verbosity = 2 if verbose else 1

    if coverage:
        from coverage import Coverage
        cover = Coverage(branch=True, source=[where])
        cover.start()

    loader = unittest.TestLoader()
    if tests:
        suite = loader.loadTestsFromNames(tests)
    else:
        suite = loader.discover(where)

    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(suite)

    if coverage:
        cover.stop()
        cover.report()


@command
def clean(config):
    for root, directories, files in os.walk('.'):
        if '__pycache__' in directories:
            shutil.rmtree(os.path.join(root, '__pycache__'))


@command
def clean_all(config, yes=False):
    prompt = 'Clean everything? You will have to re-run `make init` after this.'

    if not (yes or confirm(config, prompt)):
        print('Aborted')
        return

    clean(config)

    def rmtrees(*paths):
        for path in paths:
            if os.path.isdir(path):
                print('Removing', path)
                shutil.rmtree(path, ignore_errors=False)

    rmtrees('.env', 'dist', config.docs.build_dir, *glob.glob('*.egg-info'))


@command
def build_docs(config, overwrite=False):
    local(config, (
        'sphinx-build',
        '-E' if overwrite else '',
        config.docs.dir,
        config.docs.build_dir,
    ))


@command
def upload_docs(config):
    source = config.docs.build_dir
    if not source.endswith('/'):
        source += '/'

    destination = posixpath.join(config.docs.upload_path, config.package)
    if not destination.endswith('/'):
        destination += '/'

    url = ':'.join((config.domain_name, destination))

    print('Uploading {source} to {url}...'.format_map(locals()))

    local(config, (
        'rsync',
        '--rsync-path "sudo -u tangled rsync"',
        '-rltvz --delete',
        source, url,
    ))


__all__ = get_all_list(vars())
__all__.append('show_config')
