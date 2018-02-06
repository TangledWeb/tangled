import datetime
import os
import re
from subprocess import check_call

from tangled.abcs import ACommand
from tangled.decorators import cached_property
from tangled.util import as_bool


setup_version_pattern = (
    r'(?P<whitespace>\s*)'
    r'version=(?P<quote>(\'|"))(?P<old_version>.+)(\'|"),\s*')


class ReleaseCommand(ACommand):

    @classmethod
    def configure(cls, parser):
        parser.add_argument(
            '-r', '--release-version',
            help='Version of this release; '
                 'also used as tag name unless --tag is specified')
        parser.add_argument(
            '-n', '--next-version',
            help='Anticipated version of next release '
                 '(.dev0 will be appended)')
        parser.add_argument(
            '-t', '--tag',
            help='Specify a tag name instead of using the release version')
        parser.add_argument(
            '-c', '--change-log', default=None,
            help='Path to change log; '
                 'defaults to looking for CHANGELOG, CHANGELOG.md, or CHANGELOG.rst')
        parser.add_argument(
            '-y', '--yes', action='store_true', default=False,
            help='Perform all actions without prompting')
        parser.add_argument(
            '--pre', action='store_true', default=False,
            help='Update version and set release date')
        parser.add_argument(
            '--create-tag', action='store_true', default=False,
            help='Create tag for this release')
        parser.add_argument(
            '--post', action='store_true', default=False,
            help='Set version to next and add change log section')
        parser.add_argument(
            '--full', action='store_true', default=False,
            help='Perform all of the actions above in order '
                 '(this is the default)')

    def run(self):
        self.args.full = (
            self.args.full or
            not any((self.args.pre, self.args.create_tag, self.args.post)))

        if self.args.full:
            self.args.pre = True
            self.args.create_tag = True
            self.args.post = True

        try:
            if self.args.pre:
                if not self.pre_release():
                    return 1
            if self.args.create_tag:
                self.create_tag()
            if self.args.post:
                if not self.post_release():
                    return 1
        except KeyboardInterrupt:
            pass

    @cached_property
    def change_log(self):
        change_log = self.args.change_log
        if change_log:
            return change_log
        candidates = 'CHANGELOG', 'CHANGELOG.md', 'CHANGELOG.rst'
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        raise ValueError('Change log not specified and not discoverable')

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
            r'\s*' + release_version + r'\s+'
            r'\((?P<release_date>(\d{4}-\d{2}-\d{2}|unreleased))\)'
            r'\s*')

        def change_log_on_match(match, lines, line):
            lines.append('{} ({})\n'.format(release_version, today))

        self.update_file(
            self.change_log, change_log_pattern, change_log_on_match)

        # Update setup.py

        def setup_on_match(match, lines, line):
            whitespace = match.group('whitespace')
            quote = match.group('quote')
            lines.append(
                '{ws}version={quote}{v}{quote},\n'
                .format(ws=whitespace, v=release_version, quote=quote))

        self.update_file('setup.py', setup_version_pattern, setup_on_match)

        return self.commit(
            'Prepare release {}'.format(release_version),
            [self.change_log, 'setup.py'])

    def create_tag(self):
        tag = self.args.tag if self.args.tag else self.release_version
        check_call([
            'git', 'tag', '-a', tag, '-m',
            'Release version {}'.format(tag)])
        check_call(['git', 'log', '-p', '-1', tag])

    def post_release(self):
        if self.args.next_version:
            next_version = self.args.next_version
        else:
            next_version = input(
                'Version for new release (.dev0 will be appended): ')

        with open(self.change_log) as fp:
            content = fp.read()

        with open(self.change_log, 'w') as fp:
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

        return self.commit(
            'Back to development: {}'.format(next_version),
            [self.change_log, 'setup.py'])

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

    def commit(self, msg, files):
        check_call(['git', 'diff'] + files)
        if self.args.yes:
            commit = True
        else:
            commit = input('\n\nCommit this? [Y/n] ') or True
            commit = as_bool(commit)
        if commit:
            if not self.args.yes:
                msg = input('Commit message ["{}"] '.format(msg)) or msg
            check_call(['git', 'commit', '-m', msg] + files)
            return True
        return False
