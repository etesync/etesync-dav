# This is a CalDAV and CardDAV front-end/proxy for [EteSync](https://www.etesync.com).

![GitHub tag](https://img.shields.io/github/tag/etesync/etesync-dav.svg)
[![PyPI](https://img.shields.io/pypi/v/etesync-dav.svg)](https://pypi.python.org/pypi/etesync-dav/)
[![Chat on freenode](https://img.shields.io/badge/irc.freenode.net-%23EteSync-blue.svg)](https://webchat.freenode.net/?channels=#etesync)

This package provides a local CalDAV and CardDAV server that proxies requests
to an EteSync server for use with desktop CalDAV and CardDAV clients.

If all you want is to access your data from a computer, you are probably better off using [the web app](https://client.etesync.com).

This is essentially a compatibility layer between EteSync and DAV clients.

This depends on the [radicale_storage_etesync](https://github.com/etesync/radicale_storage_etesync) module and the [Radicale server](http://radicale.org) for operation.

**Note:** This software is still in beta. It should work well and is used daily by many users, but there may be some rough edges.

# Installation

`pip install etesync-dav`

The above should be either run as root, or better yet, inside a python "virtualenv".

**Note:** Python 3 is required.

## Arch Linux

The package `etesync-dav` is [available on AUR](https://aur.archlinux.org/packages/etesync-dav/).

## Docker

Run one time initial setup to persist the required configuration into a docker volume

    docker run -it --rm -v etesync:/data etesync/etesync-dav setup

Run etesync-dav in a background docker container with configuration from previous step (this is the command you'd run every time)

    docker run --name etesync-dav -d -v etesync:/data -p 37358:37358 --restart=always etesync/etesync-dav

Getting log output from container if you run into any issues

    docker logs etesync-dav

## Windows systems

You can either follow the Docker instructions above (get Docker [here](https://www.docker.com)), or alternatively install Python3 for windows from [here](https://www.python.org/downloads/windows).

## Python virtual environment (Linux and Mac)

Install virtual env from your package manager, for example on Arch:

    pacman -S python-virtualenv

Set up the virtual env:

    virtualenv venv
    source venv/bin/activate
    pip install etesync-dav

Run the etesync commands as explained in the "Configuration and running" section:

    ./venv/bin/etesync-dav-manage ...
    ./venv/bin/etesync-dav ...

Please note that you'll have to run `source venv/bin/activate` every time you'd like to run the EteSync commands.


# Configuration and running

If you are self-hosting the EteSync server, you will need to set the
`ETESYNC_URL` environment variable to the URL of your server. By default it
uses the official EteSync server at `https://api.etesync.com`. The commands
below all use this environment variable to determine which server to
connect to.

You need to first add an EteSync user using `etesync-dav-manage`, for example:

`etesync-dav-manage add me@etesync.com`

*On Windows systems, you may have to navigate to the location of the python script etesync-dav-manage.py (e.g. C:\Python\Python36\Scripts) and run*

`python etesync-dav-manage add me@etesync.com`

*Substitute “`me@etesync.com`” with the username or email you use with your
EteSync account or self-hosted server.*

and then run the server:
`etesync-dav`

*On Windows systems, you may have to navigate to the location of the etesync-dav.py script and run*

`python etesync-dav`

*Please note that some antivirus/internet security software may block the CalDAV/CardDAV service from running - make sure that etesync-dav is whitelisted.*

After this, set up your CalDAV/CardDAV client to use the username and password
you got from `etesync-dav-manage`, or alternatively run:
`etesync-dav-manage get me@etesync.com` to get them again.

Depending on the client you use, the server path should either be:

* `http://localhost:37358/`
* `http://localhost:37358/me@etesync.com/`

On most clients this should automatically detect your collections (i.e.
calendars and address books).

If your client does not automatically detect your collections, you will
need to manually add them. You need to find the “collection URL” for each
collection you want to add. Currently, the simplest way to do this is to
log in to the web interface provided by the internal Radicale server. Just
open [http://localhost:37358/](http://localhost:37358/) in your browser (or
substitute “localhost” for the hostname or IP address of the etesync-dav
instance). Then you will need to log in using the username and password
given by the `etesync-dav-manage` tool as described above (run `etesync-dav-manage
get me@etesync.com` to get them again). The Radicale web interface shows
the collections with their names and URLs. You can just copy and paste the
URLs into your client. You will most likely also need to manually copy and
paste the collection names as well, and select a color manually.

Alternative ways to get collection URLs include programmatically using the
`pyetesync` module (see
[example.py](https://github.com/etesync/pyetesync/blob/master/example.py)
for example usage), or copy it from the debug page in the EteSync Android
app. When using `example.py`, the EteSync server address that should be
used is `https://api.etesync.com` when interacting with the production
server.


## Config files

`etesync-dav` stores data in the directory specified by the `CONFIG_DIR`
environment variable. This includes a database, credentials, and Radicale
configuration file. This directory is not relocatable, so if you change
`CONFIG_DIR` you will need to regenerate these files (which means
reconfiguring clients). It may be possible to manually edit these files to
the new path. Note that the database will just mirror the content of your
main EteSync database so in most cases you should not lose anything if you
delete it.

`CONFIG_DIR` defaults to a subdirectory of the appropriate config directory
for your platform (`~/.config/etesync-dav` on Unix/Linux, see
[appdirs](http://pypi.python.org/pypi/appdirs) module docs for where it
will be on other platforms).

# Client support

The following clients have been tested:

* Thunderbird
    * CardDAV: Works.
        * Notes: requires the
          [CardBook](https://addons.mozilla.org/en-US/thunderbird/addon/cardbook/)
add-on, path should include the username as above, and vCard version should
be set to v4.0 when prompted
    * CalDAV: Only works when providing full collection path.
        * Requires the
          [Lightning](https://addons.mozilla.org/en-US/thunderbird/addon/lightning/)
add-on.
* OSX
    * CalDAV: Works. Setup instructions:
      * Internet Accounts->Add Other Account->CalDAV account
      * Account Type: Advanced
      * Username: me@etesync.com
      * Password: generated etesync-dav password
      * Server Address: localhost
      * Server Path: /
      * Port: 37358
      * Uncheck Use SSL (does nothing under macOS Mojave, SSL is always enabled)
    * CardDAV: Works. Setup instructions:
      * Internet Accounts->Add Other Account->CardDAV account
      * Account Type: Manual
      * Username: me@etesync.com
      * Password: generated etesync-dav password
      * Server Address: `http://localhost:37358/` (under macOS Mojave: `https://localhost:37358/`)

# macOS Mojave

macOS Mojave enforces the use of SSL, *regardless* of whether you enable the
checkbox for SSL or not. So to use EteSync, you have to enable SSL. You can
do so by using the `etesync-dav-certgen` utility. It will generate a
self-signed SSL certificate, configure etesync-dav to use that certificate,
and -- if you request that -- will make your system trust it.

You can do all of this by:

    etesync-dav-certgen --trust-cert

You will be prompted for your login password. This is because `--trust-cert`
imports the certificate into your login keychain and then instructs the
system to trust it for SSL connections.

Once you have run `etesync-dav-certgen`, you need to restart `etesync-dav`
for the changes to take effect. Then proceed to configure CalDAV and CardDAV
as described above.

If you have already configured `etesync-dav` to use SSL, 
`etesync-dav-certgen` will use your existing settings; in won't
reconfigure `etesync-dav`. It also won't overwrite existing
certificates. `--trust-cert` works on macOS 10.3 or newer only.
See `etesync-dav-certgen --help` for details.


# Known issues

* This package is missing startups script for automatic execution on startup.
