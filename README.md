# This is a python client library for [EteSync](https://www.etesync.com)

![GitHub tag](https://img.shields.io/github/tag/etesync/pyetesync.svg)
[![PyPI](https://img.shields.io/pypi/v/etesync.svg)](https://pypi.python.org/pypi/etesync/)
[![Chat on freenode](https://img.shields.io/badge/irc.freenode.net-%23EteSync-blue.svg)](https://webchat.freenode.net/?channels=#etesync)

This module provides a python API to interact with an EteSync server.
It currently implements AddressBook and Calendar access, and supports two-way
sync (both push and pull) to the server.
It doesn't currently implement pushing raw journal entries which are needed for
people implementing new EteSync journal types which will be implemented soon.

To install, please run:

```
pip install etesync
```

The module works and the API is tested (see [tests/](tests/)), however there still
may be some oddities, so please report if you encounter any.

There is one Authenticator endpoint, and one endpoint for the rest of the API
interactions.

The way it works is that you run "sync", which syncs local cache with server.
Afterwards you can either access the journal directly, or if you prefer,
you can access a collection, for example a Calendar, and interact with the
entries themselves, which are already in sync with the journal.

Check out [example.py](example.py) for a basic usage example, or the tests
for a more complete example.

While this is stable enough for usage, it still may be subject to change, so
please watch out for the changelog when updating version.
Docs are currently missing but are planned.

## Running

You'll need virtualenv to get the dependencies:

```
pip3 install virtualenv
```

Check out this repository:

```
git clone git@github.com:etesync/pyetesync.git
cd pyetesync
git checkout v0.5.0
```

Install dependencies:

```
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run `example.py` to export your data:

```
python3 example.py <email> <auth password> <encryption password> https://api.etesync.com
```

You may need to surround your passwords in quotes and you may need to escape special characters with a `\`.

And all of your data will be copied to a local database located at `~/.etesync/data.db`.
