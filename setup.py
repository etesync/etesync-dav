# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

setup(
    name='etesync',
    version='0.5.4',
    author='EteSync',
    author_email='development@etesync.com',
    url='https://github.com/etesync/pyetesync',
    description='Python client library for EteSync',
    keywords=['etesync', 'encryption', 'sync', 'pim'],
    license='LGPL',
    long_description=open('DESCRIPTION.rst').read(),
    packages=find_packages(exclude=("tests",)),
    include_package_data=True,
    install_requires=[
       'appdirs>=1.4',
       'asn1crypto>=0.22',
       'cffi>=1.10',
       'coverage>=4.3',
       'cryptography>=1.9',
       'furl>=0.5',
       'idna>=2.5',
       'orderedmultidict>=0.7',
       'packaging>=16.8',
       'peewee>=2.9,<3.0',
       'py>=1.4',
       'pyasn1>=0.2',
       'pycparser>=2.17',
       'pyparsing>=2.2',
       'pyscrypt>=1.6',
       'python-dateutil>=2.6',
       'requests>=2.13',
       'six>=1.10',
       'vobject>=0.9',
    ]
)
