# -*- coding: utf-8 -*-

"""Setup module for etesync-dav."""

import codecs
import re
from os import path

from setuptools import find_packages, setup


def read_file(filepath):
    """Read content from a UTF-8 encoded text file."""
    with codecs.open(filepath, 'rb', 'utf-8') as file_handle:
        return file_handle.read()


PKG_NAME = 'etesync-dav'
PKG_DIR = path.abspath(path.dirname(__file__))
META_PATH = path.join(PKG_DIR, PKG_NAME.replace('-', '_', 1), '__init__.py')
META_CONTENTS = read_file(META_PATH)


def load_long_description():
    """Load long description from file DESCRIPTION.rst."""
    try:
        title = f"{PKG_NAME}: {find_meta('description')}"
        head = '=' * (len(title.strip(' .')))

        contents = (
            head,
            format(title.strip(' .')),
            head,
            '',
            read_file(path.join(PKG_DIR, 'DESCRIPTION.rst')),
        )

        return '\n'.join(contents)
    except (RuntimeError, FileNotFoundError) as read_error:
        message = 'Long description could not be read from DESCRIPTION.rst'
        raise RuntimeError(f'{message}: {read_error}') from read_error


def find_meta(meta):
    """Extract __*meta*__ from META_CONTENTS."""
    meta_match = re.search(
        r"^__{meta}__\s+=\s+['\"]([^'\"]*)['\"]".format(meta=meta),
        META_CONTENTS,
        re.M
    )

    if meta_match:
        return meta_match.group(1)
    raise RuntimeError(
        f'Unable to find __{meta}__ string in package meta file'
    )


def is_canonical_version(version):
    """Check if a version string is in the canonical format of PEP 440."""
    pattern = (
        r'^([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))'
        r'*((a|b|rc)(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))'
        r'?(\.dev(0|[1-9][0-9]*))?$')
    return re.match(pattern, version) is not None


def get_version_string():
    """Return package version as listed in `__version__` in meta file."""
    # Parse version string
    version_string = find_meta('version')

    # Check validity
    if not is_canonical_version(version_string):
        message = (
            'The detected version string "{}" is not in canonical '
            'format as defined in PEP 440.'.format(version_string))
        raise ValueError(message)

    return version_string


# Dependencies that are downloaded by pip on installation and why.
INSTALL_REQUIRES = [
    'appdirs>=1.4.3',
    'etesync>=0.12.1',
    'etebase>=0.30.0',
    'msgpack>=1.0.0',
    'Radicale>=3.0.3,<=3.1.0',
    'Flask>=1.1.1',
    'Flask-WTF>=0.14.2',
    'requests[socks]>=2.21',
    'pyobjc-framework-Cocoa>=7.0.0 ; sys_platform=="darwin"',
]

KEYWORDS = [
    'etesync',
    'encryption',
    'sync',
    'pim',
    'caldav',
    'carddav'
]

# Project's URLs
PROJECT_URLS = {
    'Documentation': f"{find_meta('url')}/blob/master/README.md#installation",
    'Changelog': f"{find_meta('url')}/blob/master/ChangeLog.md",
    'Bug Tracker': f"{find_meta('url')}/issues",
    'Source Code': find_meta('url'),
}

if __name__ == '__main__':
    setup(
        name=PKG_NAME,
        version=get_version_string(),
        author=find_meta('author'),
        author_email=find_meta('author_email'),
        license=find_meta('license'),
        description=find_meta('description'),
        long_description=load_long_description(),
        long_description_content_type='text/x-rst',
        keywords=KEYWORDS,
        url=find_meta('url'),
        project_urls=PROJECT_URLS,
        packages=find_packages(exclude=["tests"]),
        platforms='any',
        include_package_data=True,
        zip_safe=False,
        python_requires='>=3',
        install_requires=INSTALL_REQUIRES,
        scripts=[
            'scripts/etesync-dav',
        ],
    )
