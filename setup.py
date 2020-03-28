# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

exec(open('etesync_dav/_version.py').read())

setup(
    name='etesync-dav',
    version=__version__,
    author='Tom Hacohen',
    author_email='tom@stosb.com',
    url='https://github.com/etesync/etesync-dav',
    description='A CalDAV and CardDAV frontend for EteSync',
    keywords=['etesync', 'encryption', 'sync', 'pim', 'caldav', 'carddav'],
    license='GPL-3.0-only',
    long_description=open('DESCRIPTION.rst').read(),
    packages=find_packages(),
    scripts=[
        'scripts/etesync-dav',
    ],
    include_package_data=True,
    install_requires=[
        'appdirs>=1.4.3',
        'etesync>=0.11.1',
        'Radicale==2.1.11',
        'Flask>=1.1.1',
        'Flask-WTF>=0.14.2',
    ]
)
