This is a CalDAV and CardDAV front-end for [EteSync](https://www.etesync.com).

This package provides a local CalDAV and CardDAV server that proxies requests
to an EteSync server for use with desktop CalDAV and CardDAV clients.

This is essentially a compatibility layer between EteSync and DAV clients.

This depends on the [radicale_storage_etesync](https://github.com/etesync/radicale_storage_etesync) module and the [Radicale server](http://radicale.org) for operation.

# Installation

`pip install etesync-dav`

# Configuration and running

You need to first add an EteSync user using `etesync-dav-manage`, for example:

`etesync-dav-manage add me@etesync.com`

and then run the server:
`etesync-dav`

After this, set up your CalDAV/CardDAV client to use the username and password
you got from `etesync-dav-manage`, or alternatively run:
`etesync-dav-manage get me@etesync.com` to get them again.

Depending on the client you use, the server path should either be:

* `http://localhost:37358/`
* `http://localhost:37358/me@etesync.com/`

On most clients this should automatically detect your calendars/address books.
If it doesn't, it means you'd have to set your exact collection url for each
collection which is not trivial to get at this point. In order to get it, you'd
either need to get it using [example.py](https://github.com/etesync/pyetesync/blob/master/example.py) from pyetesync,
or copy it from the debug page in the EteSync app.

# Client support

The following clients have been tested:

* Thunderbird
    * CardDAV: Works.
        * Notes: requires the CardBook plugin, path should include the username as above, and vCard version should be set to v4.0 when prompted
    * CalDAV: Only works when providing full collection path.

# Known issues

* This package is missing startups script for automatic execution on startup.
* Due to an issue with one of the dependencies, some contacts, namely groups, will sometimes fail to work. Revelant PR: https://github.com/eventable/vobject/pull/77
