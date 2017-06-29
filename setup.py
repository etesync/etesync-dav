# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

setup(
    name='etesync-dav',
    version='0.1.1',
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
        'scripts/etesync-dav-manage'
    ],
    include_package_data=True,
    install_requires=[
        'appdirs>=1.4.3',
        'radicale_storage_etesync>=0.1.2',
    ]
)
