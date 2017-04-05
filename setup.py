# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

setup(
    name='etesync',
    version='0.3.0',
    author='EteSync',
    author_email='development@etesync.com',
    url='https://github.com/etesync/pyetesync',
    description='Python client library for EteSync',
    keywords=['etesync', 'encryption', 'sync', 'pim'],
    license='LGPL',
    long_description=open('README.md').read(),
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
       'appdirs>=1.4',
       'furl>=0.5',
       'orderedmultidict>=0.7',
       'packaging>=16.8',
       'peewee>=2.9',
       'pyaes>=1.6',
       'pyparsing>=2.2',
       'pyscrypt>=1.6',
       'python-dateutil>=2.6',
       'six>=1.10',
       'vobject>=0.9',
    ]
)
