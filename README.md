This is a python client library for [EteSync](https://www.etesync.com)

This module provides a python API to interact with an EteSync server.
It currently implements AddressBook and Calendar access, and supports two-way
sync (both push and pull) to the server.
It doesn't currently implement pushing raw journal entries which are needed for
people implementing new EteSync journal types which will be implemented soon.

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
