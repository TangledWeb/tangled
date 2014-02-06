import datetime
import re
from subprocess import check_call

from tangled.abcs import ACommand
from tangled.converters import as_bool
from tangled.decorators import cached_property


setup_version_pattern = (
    r'(?P<whitespace>\s*)'
    r'version=(?P<quote>(\'|"))(?P<old_version>.+)(\'|"),\s*')


class ReleaseCommand(ACommand):

    @classmethod
    def configure(cls, parser):
        parser.add_argument('-r', '--release-version')
        parser.add_argument('-n', '--next-version')
        parser.add_argument('-t', '--tag')
        parser.add_argument('-c', '--change-log', default='CHANGELOG')
        parser.add_argument('--pre', action='store_true', default=False)
        parser.add_argument('--create-tag', action='store_true', default=False)
        parser.add_argument('--upload', action='store_true', default=False)
        parser.add_argument('--post', action='store_true', default=False)
        parser.add_argument('--full', action='store_true', default=False)

    def run(self):
        self.args.full = (
            self.args.full or
            not any((
                self.args.pre, self.args.create_tag, self.args.upload,
                self.args.post)))

        if self.args.full:
            self.args.pre = True
            self.args.create_tag = True
            self.args.upload = True
            self.args.post = True

        try:
            if self.args.pre:
                self.pre_release()
            if self.args.create_tag:
                self.create_tag()
            if self.args.upload:
                self.upload()
            if self.args.post:
                self.post_release()
        except KeyboardInterrupt:
            self.exit('\nAborted')

    @cached_property
    def release_version(self):
        if self.args.release_version:
            release_version = self.args.release_version
        else:
            release_version = input('Version for new release: ')
        return release_version

    def pre_release(self):
        release_version = self.release_version
        today = datetime.date.today().strftime('%Y-%m-%d')

        # Update change log

        change_log_pattern = (
            r'\s*'
            + release_version +
            r'\s+'
            r'\((?P<release_date>(\d{4}-\d{2}-\d{2}|unreleased))\)'
            r'\s*')

        def change_log_on_match(match, lines, line):
            lines.append('{} ({})\n'.format(release_version, today))

        self.update_file(
            self.args.change_log, change_log_pattern, change_log_on_match)

        # Update setup.py

        def setup_on_match(match, lines, line):
            whitespace = match.group('whitespace')
            quote = match.group('quote')
            lines.append(
                '{ws}version={quote}{v}{quote},\n'
                .format(ws=whitespace, v=release_version, quote=quote))

        self.update_file('setup.py', setup_version_pattern, setup_on_match)

        self.commit_or_abort(
            'Prepare release {}'.format(release_version),
            [self.args.change_log, 'setup.py'])

    def create_tag(self):
        tag = self.args.tag if self.args.tag else self.release_version
        check_call([
            'git', 'tag', '-a', tag, '-m',
            'Release version {}'.format(tag)])
        check_call(['git', 'log', '-p', '-1', tag])

    def upload(self):
        upload_to_pypi = input('Create sdist and upload to PyPI? [y/N] ')
        upload_to_pypi = as_bool(upload_to_pypi or False)
        if upload_to_pypi:
            check_call(['python', 'setup.py', 'sdist', 'register', 'upload'])

    def post_release(self):
        if self.args.next_version:
            next_version = self.args.next_version
        else:
            next_version = input(
                'Version for new release (.dev0 will be appended): ')

        with open(self.args.change_log) as fp:
            content = fp.read()

        with open(self.args.change_log, 'w') as fp:
            header = '{} (unreleased)'.format(next_version)
            separator = '=' * len(header)
            fp.writelines([
                header, '\n',
                separator, '\n',
                '\n'
                '- No changes yet\n'
                '\n\n'
            ])
            fp.write(content)

        next_version += '.dev0'

        def setup_on_match(match, lines, line):
            whitespace = match.group('whitespace')
            quote = match.group('quote')
            lines.append(
                '{ws}version={quote}{v}{quote},\n'
                .format(ws=whitespace, v=next_version, quote=quote))

        self.update_file('setup.py', setup_version_pattern, setup_on_match)

        self.commit_or_abort(
            'Back to development: {}'.format(next_version),
            [self.args.change_log, 'setup.py'])

    def update_file(self, file_name, pattern, on_match, on_not_found=None):
        """Update line in file matching pattern."""
        pattern = re.compile(pattern)
        lines = []

        with open(file_name) as fp:
            line = fp.readline()
            while line:
                match = pattern.match(line)
                if match:
                    on_match(match, lines, line)
                    lines.append(fp.read())
                    break
                lines.append(line)
                line = fp.readline()
            else:
                if on_not_found:
                    on_not_found()

        with open(file_name, 'w') as fp:
            fp.write(''.join(lines))

    def commit_or_abort(self, msg, files):
        check_call(['git', 'diff'] + files)
        commit = input('\n\nCommit this? [Y/n] ') or True
        commit = as_bool(commit)
        if commit:
            msg = input('Commit message ["{}"] '.format(msg)) or msg
            check_call(['git', 'commit', '-m', msg] + files)
        else:
            self.exit('Aborted')


