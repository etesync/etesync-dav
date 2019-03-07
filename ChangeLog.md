# Changelog

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
