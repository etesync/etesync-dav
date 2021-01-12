# Changelog

## Version 0.30.7
* Fix macOS (wrongfully) complaining that app isn't responding

## Version 0.30.6
* Fix SSL certificate generation (introduced in the previous release)

## Version 0.30.5
* Change how we generate SSL certificates to not allow them to be used as CA
* Build binaries for aarch64 on Linux

## Version 0.30.4
* Make it more obvious that users need to copy the DAV password
* Fix crash when trying to operate on deleted/non-existent items

## Version 0.30.3
* Sync: fix syncing of item deletions.
* Update etebase dep

## Version 0.30.2
* Simplify locking mechanism and fix cache eviction for changed etebase creds.
* Delete the user cache when removing user
* Creating default collections: skip creating them if fails (e.g. for associate accounts)
* Fix new collection init.
* etebase cache: add missing on_delete.

## Version 0.30.1
* Fixed race condition when there are many connections in parallel.

## Version 0.30.0
* More efficient fetching
* Update etebase dep

## Version 0.20.4
* Refresh the auth token on every web ui login

## Version 0.20.3
* Don't automatically bind to both ipv4 and ipv6 - fix detecting if ipv6 is available.

## Version 0.20.2
* Fix issue with changes not being pushed immediately after they are made.

## Version 0.20.1
* Added travis CI for CI/CD
* Improve SSL message on Windows
* Update etesync dep

## Version 0.20.0
* Windows: add an easy way to generate an SSL certificate (just like on the mac)

## Version 0.19.0
* Sync: change the sync back to being synchronous instead of async.
* Change default collection names from Default to something descriptive
* Add socks SOCKS proxy support

## Version 0.18.1
* Fix sync issues (regression in 0.18.0)
* Fix database is locked errors that were showing in some cases
* Open the default web browser to the web UI on first run

## Version 0.18.0
* Update Radicale to 3.0.0 and adjust the code accordingly
* Add a way to shutdown etesync-dav from the web UI
* Prevent Radicale from loading the default config (and confuse etesync-dav)
* Fix error message for wrong encryption passwords
* Make it possible to bind to multiple hosts + bind to both ipv4 and 6 by default

## Version 0.17.1
* Fix address book collections reporting they are also CalDAV collections

## Version 0.17.0
* Web UI: correctly redirect using https when ssl is on.
* Add application icon to macOS and Windows binaries

## Version 0.16.0
* Update pyetesync version to improve sync time and set the user agent when making requests.

## Version 0.15.1
* Update pyetesync version to fix database locking issue

## Version 0.15.0
* Webui: move it under /.web instead of a separate thread + port.
* Make permissions to config dir more restrictive.
* Move the app's data to user_data_dir from user_config_dir

## Version 0.14.3
* Provide more explicit copyright and licensing information.

## Version 0.14.2
* Fix "database is locked" errors

## Version 0.14.1
* Fix issue with high CPU usage when there's no connection.

## Version 0.14.0
* Initialise new accounts and verify encryption keys when adding users

## Version 0.13.0
* Significantly improve sync speed by changing the transaction locking mechanism
* Sync on client requests even if sync period hasn't passed (but only if two minutes have passed)
* Add support for contact PHOTOS
* Webui: add a version string to the UI so it's easier for people to know what version they are running.

## Version 0.12.0
* Sync with etesync periodically: makes it much more responsive and fixes timeout issues
* Webui: respect the ETESYNC_LISTEN_ADDRESS env var (fixes web ui access from docker)

## Version 0.11.0
* Transparently transform vCard 4.0 to 3.0 which should fix sync on macOS (which doesn't support 4.0)
* Webui: fix links to journals when SSL is enabled

## Version 0.10.0
* Webui: fix empty journal list when just adding an account.
* Add ETESYNC_DAV_URL to be able to override the DAV url from the environment.

## Version 0.9.1
* Fix pip setup.

## Version 0.9.0
* Move certgen into the main script (and generated binaries)
* Simplify and fixed issues with certgen
* Automatically use SSL if certificate and key exist.
* macOS: add a warning in the webui when missing SSL and add a button to set it up.

## Version 0.8.1
* Make it possible to override the etesync database filename from the env.
* Docker: expose web management port

## Version 0.8.0
* UI: add a web UI to manage etesync-dav
* Get rid of the need for radicale.conf (pass the needed settings directly)
* Move the radicale_storage_etesync module into the etesync_dav module

## Version 0.7.1
* Filter out the PHOTO field from contacts to fix sync (see #65 for details).
* Fixed bulk item uploading for newly created collections.
* Fixed filename generation when creating items.

## Version 0.7.0
* Merge radicale-storage-etesync into this package

## Version 0.6.0
* Upgrade radicale_etesync.
* Print correct version when passed the --version flag.

## Version 0.5.0
* Merge etesync-dav-manage and etesync-dav into a single entry point
* Add support for PyInstaller (and thus building standalone binaries).

## Version 0.4.0
* Include the new rights module (read only journals) in the default config
* Upgrade radicale_etesync.

## Version 0.3.0
* Docker: make the container run as an unprivileged user.
* Fix etesync-dav-manage to not create a database (as it doesn't need to)
* Upgrade radicale_etesync.

## Version 0.2.1
* Upgrade radicale_etesync - fixes potential intetgrity issue

## Version 0.2.0
* Upgrade radicale_etesync (adds Tasks support!)

## Version 0.1.7
* Upgrade radicale_etesync.

## Version 0.1.6
* Upgrade radicale_etesync.

## Version 0.1.5
* Upgrade radicale_etesync.

## Version 0.1.4
* Added a way to override the config path from the environment

## Version 0.1.3
* Fix issue with the config dir not being created if more than 1 level deep.

## Version 0.1.2
* Fix to work with Radicale version >= 2.1.0. - Thanks to @LogicalDash for reporting.

## Version 0.1.1
* Remove dependency on Python 3.6 and up. Should now work on any Python 3.

## Version 0.1.0
* Initial release.


# Changelog (radicale-storage-etesync before the merge)

## Version 0.9.1
* Increase required pyetesync version to 0.8.4

## Version 0.9.0
* Stop rewriting URLs to use the UID as the path and just use whatever the DAV clients choose (instead of rewriting).
  * This fixes KAddressBook and probably some other clients.

## Version 0.8.0
* Fix support for paths/UIDs that contain front slashes (/)
* Fix potential issues with making collections - although it's meant to be blocked in the rights module
* Improve warning about sync-tokens (state that they can be ignored)
* Make the module's version available in code
* Configuration: add support for shell expansion for paths
* Minor bug fixes

## Version 0.7.0
* Bring back the EteSync cache - also fixes the request throttling

## Version 0.6.0
* Allow overriding the API endpoint used, by setting ETESYNC_URL.
* Fix a serious race condition in multi-threaded environments (default with Radicale!)
  This could cause data leak when using the same etesync-dav instance with multiple EteSync credentials (not a common usecase).

## Version 0.5.1
* Rights management: better handle 404s

## Version 0.5.0
* Add a rights module to handle read only journals.
* Bump pyetesync version

## Version 0.4.0
* Make it possible to have a different database per user
* Make the sync throttle per user rather than instance
* Verify that the user creds haven't changed or removed before using the cached etesync.
* Creds: only reload the file if it has changed.
* Fix fetching of user info to always fetch from the server.

## Version 0.3.0
* Fetch user info on every sync
* Reload credentials file when trying to access credentials of a user that's not found.
* Bump pyetesync version

## Version 0.2.1
* Bump pyetesync version that fixes potential integrity issue

## Version 0.2.0
* Add support for tasks
* Correctly advertise calendars only support vevents.

## Version 0.1.8
* Ignore journals of unknown types
* Bump pyetesync version

## Version 0.1.7
* Bump pyetesync version

## Version 0.1.6
* Fix a few weird behaviours that should improve compatability
* Got Apple Calendar to work (but not Contacts)
* Workaround the Radicale bug in 2.1.10
* Update radicale minimum version requirements

## Version 0.1.5
* Upgrade pyetesync and radicale

## Version 0.1.4
* Upgrade pyetesync version requirement

## Version 0.1.3
* Fix to work with Radicale version >= 2.1.0 - Thanks to @LogicalDash for reporting.

## Version 0.1.2
* Credential files:
    * Fix loading of empty credential files
    * Fix saving of credential files
* Collections:
    * Fix collection serialization
    * Fix setting of owner

## Version 0.1.1
* Initial release. Everything should work apart of Last-Modified.
