import os
import pkg_resources
import unittest

from tangled.abcs import ACommand


class TestCommand(ACommand):

    """A simple wrapper around Python's built-in unittest discovery.

    Displays a coverage report by default.

    I was having some problems with Nose and Python 3.3 namespace
    packages. Hopefully that will be fixed soon, and this can go
    away.

    """

    @classmethod
    def configure(cls, parser):
        parser.add_argument('--where', default=None)
        parser.add_argument(
            '--with-coverage', action='store_true', default=True)
        parser.add_argument('tests', nargs='*', default=None)

    def run(self):
        where = self.args.where
        if where is None:
            dist = next(pkg_resources.find_distributions('.'), True)
            where = os.path.join('.', *dist.project_name.split('.'))

        print('Running tests from {}'.format(where))

        with_coverage = self.args.with_coverage
        if with_coverage:
            import coverage
            cov = coverage.coverage(branch=True, source=[where])
            cov.start()

        loader = unittest.TestLoader()
        if self.args.tests:
            suite = loader.loadTestsFromNames(self.args.tests)
        else:
            suite = loader.discover(where)

        runner = unittest.TextTestRunner()
        runner.run(suite)

        if with_coverage:
            cov.stop()
            cov.report()
