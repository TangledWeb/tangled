1.0a13 (unreleased)
===================

- No changes yet


1.0a12 (2017-12-13)
===================

- Replaced `tangled test` script with RunCommands equivalent.
- Added `--upgrade` flag to `install` command.
- Removed `--upload` option from `tangled release` script; I'm not sure why,
  but this was creating borked distributions.
- Reimplemented all make targets as RunCommands commands; only `init` remains
  as a wrapper around `run init`.
- Removed remaining vestiges of Buildout :(


1.0a11 (2017-12-09)
===================

Release of 1.0a10 to PyPI was borked. This fixes that.


1.0a10 (2017-12-09)
===================

- Added abilitiy for properties created via the `cached_property` decorator to
  specify their dependencies.
- Made `cached_property` thread safe (or at least made an initial attempt at
  that). Inspired by by https://github.com/pydanny/cached-property.
- Made `util.random_string()` use the Base 64 alphabet by default instead of
  grabbing 16 bytes via `os.urandom()` and encoding them as a 32-byte hex
  string.


0.1a9 (2016-01-03)
==================

- Remove custom `find_packages` function in favor of setuptools'
  `PEP420PackageFinder`
- Add `as_self` converter; use it as the default converter (i.e., return it
  when `None` is passed to `get_converter`)
- Add `as_func_args` and `as_meth_args` converters; these are similar to
  `as_args` but automatically figure out which converters to use for a function
  or method and return a single dict of all args (instead of positionals and
  keyword args seperately)
- Add `util.is_asset_path()` for more robust, centralized checking of whether
  a string looks like an asset path
- When loading settings from a file, add `__dir__` to the settings instead of
  `__here__` as the former seems more obvious (i.e., the directory containing
  the settings file)
- When a settings file extends another settings file and the path to the
  extended file is a relative path (i.e., when the `extends` setting is
  relative, typically just a file name), assume that the path is relative to
  `__dir__`; previously, CWD was used implicitly
- Use extended (Buildout-style) interpolation by default when reading settings
  files; the extended interpolation syntax is nicer to work with and more
  flexible than basic interpolation

0.1a8 (2014-08-04)
==================

- Consolidated `cached_property` and `reify` decorators; removed `reify`.
- Added a find_packages() function that is similar to setuptools'
  find_packages(). This version does the "right thing" with regard to PEP 420
  namespace packages--i.e., it treats *every* directory as a package. The
  quotes around "right thing" indicate that it's debatable as to whether this
  is correct in the general case.
- util.fully_qualified_name() can now accept a module as an argument; before,
  it would blow up if a module was passed in.
- Implemented a "deferred decorator action" system that is similar to Venusian
  but much simpler. Venusian uses all kinds of frame inspection/modification
  hackery that is really hard to understand.


0.1a7 (2014-03-22)
==================

- Make `converters.as_seq_of_seq()` return a converter (it no longer directly
  takes a value to convert). This makes it consistent with the other sequence
  converters.
- Add `tangled.settings.check_required()` to the public API to indicate that
  settings tools/parsers can use it.
- Remove `processors` arg from `settings.parse_settings()`. It didn't serve any
  purpose, and its presence was confusing.
- Remove custom bdist_egg command that ensured "missing" `__init__.py` files
  weren't added. It's no longer needed since setuptools 3+ no longer does
  this.
- Bug fix: Add missing `settings` arg to `check_required()` call in
  `settings.parse_settings_file()`.
- Reenable running doctests by default when running nosetests.
- Upgrade nose from 1.3.0 to 1.3.1
- Upgrade Sphinx from 1.2.1 to 1.2.2


0.1a6 (2014-03-06)
==================

- Fix/improve package metadata.
- Add workaround for setuptools "helpfully" adding __init__.py to
  tangled namespace.


0.1a5 (2014-02-09)
==================

- Allow .py files in scaffolds to have a .template suffix. This is necessary
  for .py files that use `${var}`s that aren't inside strings. Otherwise, those
  files will cause a `SyntaxError` when the package containing the scaffold is
  installed.


0.1a4 (2014-02-06)
==================

- Add `tangled python` command
- Add -y flag to `tangled release` command (assume answer to all prompts is
  yes)
- Don't offer to push tags in `tangled release`; pushing stuff is outside the
  scope of this tool.


0.1a3 (2014-02-06)
==================

- Really fix packaging issues


0.1a2 (2014-02-05)
==================

- Fix packaging issues


0.1a1 (2014-02-05)
==================

- Initial version
