from setuptools import setup, PEP420PackageFinder


setup(
    name='tangled',
    version='1.0a13.dev0',
    description='Tangled namespace and utilities',
    long_description=open('README.rst').read(),
    url='https://tangledframework.org/',
    download_url='https://github.com/TangledWeb/tangled/tags',
    author='Wyatt Baldwin',
    author_email='self@wyattbaldwin.com',
    packages=PEP420PackageFinder.find(include=['tangled*']),
    install_requires=[
        'runcommands>=1.0a27',
    ],
    extras_require={
        'dev': [
            'coverage>=4.4.2',
            'flake8>=3.5.0',
            'Sphinx>=1.6.5',
            'sphinx_rtd_theme>=0.2.4',
        ],
    },
    entry_points="""
    [console_scripts]
    tangled = tangled.__main__:main

    [tangled.scripts]
    release = tangled.scripts:ReleaseCommand
    scaffold = tangled.scripts:ScaffoldCommand
    python = tangled.scripts:ShellCommand

    """,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)
