# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

exec(open('radicale_storage_etesync/_version.py').read())

setup(
    name='radicale_storage_etesync',
    version=__version__,
    author='EteSync',
    author_email='development@etesync.com',
    url='https://github.com/etesync/radicale_storage_etesync',
    description='An EteSync storage plugin for Radicale',
    keywords=['etesync', 'encryption', 'sync', 'pim', 'radicale'],
    license='GPL',
    long_description=open('DESCRIPTION.rst').read(),
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'etesync>=0.8.0',
        'Radicale>=2.1.10',
    ]
)
