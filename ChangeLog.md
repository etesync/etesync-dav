# Changelog

## Version 0.6.2
* Add shell scripts for executing tests

## Version 0.6.1
* Fix journal integrity issue when syncing more than one collection item.

## Version 0.6.0
* Add tasks support

## Version 0.5.6
* Fix broken calling to scrypt
* Fix sync (was broken in some cases) and tests

## Version 0.5.5
* Automatically detect if scrypt is available. If so use it, otherwise revert to pyscript. Setup.py dep remains on pyscypt.
  * This is to help distors that don't package pyscrypt
* Update peewee to support version 3 and up

## Version 0.5.4
* Fix peewee dep to be < 3.0.0

## Version 0.5.3
* Change back to pyscript, because scrypt has proven very problematic
* Update all the deps

## Version 0.5.2
* Don't install tests as a package

## Version 0.5.1
* Change from pyscrypt to scrypt (much faster and widely adopted)

## Version 0.5.0
* Add functions to check if the journal list or journals are dirty.
* Add a nicer way to access the journal's info.
* Fix an issue with caching user info
* Improve tests
