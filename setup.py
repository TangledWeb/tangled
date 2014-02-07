from setuptools import setup


setup(
    name='tangled',
    version='0.1a5.dev0',
    description='Tangled namespace and utilities',
    long_description=open('README.rst').read(),
    url='http://tangledframework.org/',
    author='Wyatt Baldwin',
    author_email='self@wyattbaldwin.com',
    packages=[
        'tangled',
        'tangled.scripts',
        'tangled.tests',
        'tangled.tests.dummy_package',
    ],
    extras_require={
        'dev': (
            'coverage>=3.7.1',
            'nose>=1.3.0',
            'pep8>=1.4.6',
            'pyflakes>=0.7.3',
            'Sphinx>=1.2.1',
            'sphinx_rtd_theme>=0.1.5',
        )
    },
    entry_points="""
    [console_scripts]
    tangled = tangled.__main__:main

    [tangled.scripts]
    release = tangled.scripts:ReleaseCommand
    scaffold = tangled.scripts:ScaffoldCommand
    python = tangled.scripts:ShellCommand
    test = tangled.scripts:TestCommand

    """,
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
)
