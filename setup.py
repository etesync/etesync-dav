# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

exec(open('etesync_dav/_version.py').read())

setup(
    name='etesync-dav',
    version=__version__,
    author='EteSync',
    author_email='development@etesync.com',
    url='https://github.com/etesync/etesync-dav',
    description='A CalDAV and CardDAV frontend for EteSync',
    keywords=['etesync', 'encryption', 'sync', 'pim', 'caldav', 'carddav'],
    license='GPL',
    long_description=open('DESCRIPTION.rst').read(),
    packages=find_packages(),
    scripts=[
        'scripts/etesync-dav',
        'scripts/etesync-dav-certgen'
    ],
    include_package_data=True,
    install_requires=[
        'appdirs>=1.4.3',
        'etesync>=0.9.0',
        'Radicale>=2.1.10',
    ]
)
