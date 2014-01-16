from setuptools import setup, find_packages


setup(
    name='tangled',
    version='0.1.dev0',
    description='Tangled namespace and utilities',
    long_description=open('README.rst').read(),
    packages=find_packages(),
    extras_require={
        'dev': (
            'coverage>=3.7.1',
            'pep8>=1.4.6',
            'pyflakes>=0.7.3',
            'pytest>=2.5.1',
            'pytest-cov>=1.6',
            'Sphinx>=1.2',
            'sphinx_rtd_theme>=0.1.5',
        )
    },
    entry_points="""
    [console_scripts]
    tangled = tangled.__main__:main

    [tangled.scripts]
    test = tangled.scripts:TestCommand

    """,
    classifiers=(
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ),
)
