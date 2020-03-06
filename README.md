<p align="center">
  <img width="120" src="icon.svg" />
  <h1 align="center">EteSync - Secure Data Sync</h1>
</p>

This is a CalDAV and CardDAV adapter for [EteSync](https://www.etesync.com)

![GitHub tag](https://img.shields.io/github/tag/etesync/etesync-dav.svg)
[![PyPI](https://img.shields.io/pypi/v/etesync-dav.svg)](https://pypi.python.org/pypi/etesync-dav/)
[![Chat on freenode](https://img.shields.io/badge/irc.freenode.net-%23EteSync-blue.svg)](https://webchat.freenode.net/?channels=#etesync)

This package provides a local CalDAV and CardDAV server that acts as an EteSync compatibility layer (adapter).
It's meant for letting desktop CalDAV and CardDAV clients such as Thunderbird, Outlook and Apple Contacts connect with EteSync.

If all you want is to access your data from a computer, you are probably better off using [the web app](https://client.etesync.com).

**Note:** This software is still in beta. It should work well and is used daily by many users, but there may be some rough edges.

# Installation

The easiest way to start using etesync-dav is by getting one of the pre-built binaries from the [releases page](https://github.com/etesync/etesync-dav/releases).

These binaries are self-contained and can be run as-is, though they do not start automatically on boot. You'd need to either start them manually, or set up autostart based on your OS.

# Configuration and running

1. Run `etesync-dav` and open the management UI in your browser: http://localhost:37358/
2. Add your EteSync user through the web UI.
3. Copy the DAV specific password by click the "Copy Password" button next to your newly added username.

For advanced usage and CLI instructions please refer to [the advanced usage section](#advanced-usage).

*Please note that some antivirus/internet security software may block the CalDAV/CardDAV service from running - make sure that etesync-dav is whitelisted.*

Don't forget to set up EteSync to automatically start on startup. Instructions for this are unfortunately OS dependent and out of scope for this README.

# Setting up clients

You now need to set up your CalDAV/CardDAV client using your username and the password you got in the previous step.

Depending on the client you use, the server path should either be:

* `http://localhost:37358/`
* `http://localhost:37358/user@example.com/`

On most clients this should automatically detect your collections (i.e.
calendars and address books).

If your client does not automatically detect your collections, you will
need to manually add them. You can find the links in the management UI
when you click on your username.

## Specific client notes and instructions

### Thunderbird
1. Install [TbSync](https://addons.thunderbird.net/en-us/thunderbird/addon/tbsync/) and the accompanying [DAV provider](https://addons.thunderbird.net/en-us/thunderbird/addon/dav-4-tbsync/).
2. Open the TbSync window: Edit -> TbSync
3. Add new DAV account (choose manual configuration).
4. Use `http://localhost:37358/user@example.com/` for both servers, your EteSync username as the username and the DAV password you got in [configuration and running](#configuration-and-running) as the password.

### Evolution / GNOME Calendar / GNOME Contacts
GNOME Calendar and Contacts do not support adding WebDAV calendars and address books directly, but you can add them in Evolution and they will appear correctly in all the apps.

1. Open Evolution and click File -> New -> Calendar (or address book, depending on what you're adding).
2. Set type to CalDAV (CardDAV for address books) - Do **not** set "One The Web"
3. Use `http://localhost:37358/user@example.com/` as the server.
4. Put your username (user@example.com) in the user field, and when prompted, the DAV password you got in [configuration and running](#configuration-and-running).
5. Click "Find Calendars" and choose your wanted calendar.
6. Click OK

Repeat this for every calendar and address book you would like to add.

### macOS (Contacts.app and Calendar.app)
While EteSync-DAV works great on macOS, due to bugs in macOS Mojave, the instructions require a few extra steps for syncigng with Contacts.app and Calendar.app. Other clients, such as Thunderbird, do no require these extra steps.

Please take a look at the [macOS instructions](macos-instructions.md) for more information.

### iOS

By default, iOS only syncs events 30 days old and newer, which may look as if
events are not showing. To fix this, got to: Settings -> Calendar -> Sync and
change to the wanted time duration.

Or better yet, just use the [EteSync iOS client](https://github.com/etesync/ios).

# Alternative Installation Methods

This methods are not as easy as the pre-built binaries method above, but are also simple. Please follow the instructions below, following which follow the instructions in the [Configuration and running](#configuration-and-running) section below.

## Docker

Run one time initial setup to persist the required configuration into a docker volume. Check out the configuration section below for more information.

    docker run -it --rm -v etesync-dav:/data etesync/etesync-dav manage add USER_EMAIL

Run etesync-dav in a background docker container with configuration from previous step. This wil (re)start the container on boot and after crashes.

    docker run --name etesync-dav -d -v etesync-dav:/data -p 37358:37358 --restart=always etesync/etesync-dav
    
After this, refer to the [Setting up clients](#setting-up-clients) section below and start using it!

### Updating

To update to the latest version of the docker image, run:

    docker pull etesync/etesync-dav

### Note for self-hosting:

If you're self-hosting the EteSync server, you will need to add the following before the `-v` in the above commands:

    --env "ETESYNC_URL=https://your-etesync-url.com"
    
        
## Arch Linux

The package `etesync-dav` is [available on AUR](https://aur.archlinux.org/packages/etesync-dav/).

## Windows systems

You can either follow the Docker instructions above (get Docker [here](https://www.docker.com)), or alternatively install Python3 for windows from [here](https://www.python.org/downloads/windows).

## Python virtual environment (Linux, BSD and Mac)

Install virtual env (for **Python 3**) from your package manager, for example:

- Arch Linux: pacman -S python-virtualenv
- Debian/Ubuntu: apt-get install python3-virtualenv

The bellow commands will install etesync to a directory called `venv` in the local path. To install to a different location, just choose a different path in the commands below.

Set up the virtual env:

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install etesync-dav

Run the etesync commands as explained in the [Configuration and running](#configuration-and-running) section:

    ./venv/bin/etesync-dav manage ...
    ./venv/bin/etesync-dav ...

Please note that you'll have to run `source venv/bin/activate` every time you'd like to run the EteSync commands.

# Advanced usage

## CLI

1. Open a terminal and navigate to the binary's loctaion by typing `cd /path/to/file` (most likely `cd ~/Downloads`).
2. Rename the binary to `etesync-dav` for ease of use, by e.g: `mv linux-etesync-dav etesync-dav`
3. Make it executable: `chmod +x etesync-dav`

You need to first add an EteSync user using `./etesync-dav manage`, for example:

`./etesync-dav manage add user@example.com`

*Substitute `user@example.com` with the username or email you use with your
EteSync account or self-hosted server.*

and then run the server:
`./etesync-dav`


## Self-hosting

If you are self-hosting the EteSync server, you will need to set the
`ETESYNC_URL` environment variable to the URL of your server every time
you run etesync-dav.
By default it uses the official EteSync server at `https://api.etesync.com`.

## Using a proxy

EteSync-DAV should automatically use the system's proxy settings if set correctly. Alternatively, you can set the `HTTP_PROXY` and `HTTPS_PROXY` environment variables to manually set the proxy settings.


## Config files

`etesync-dav` stores data in the directory specified by the `ETESYNC_CONFIG_DIR`
environment variable. This includes a database and the credentials cache.
This directory is not relocatable, so if you change
`ETESYNC_CONFIG_DIR` you will need to regenerate these files (which means
reconfiguring clients). It may be possible to manually edit these files to
the new path. Note that the database will just mirror the content of your
main EteSync database so in most cases you should not lose anything if you
delete it.

`ETESYNC_CONFIG_DIR` defaults to a subdirectory of the appropriate config directory
for your platform (`~/.config/etesync-dav` on Unix/Linux, see
[appdirs](http://pypi.python.org/pypi/appdirs) module docs for where it
will be on other platforms).

# Credits

This depends on the [Radicale server](http://radicale.org) for operation.
