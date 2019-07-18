# Changelog

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
