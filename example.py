#!/usr/bin/env python

import sys

import etesync as api


def printJournal(entry):
    print("UID {} (version: {})".format(entry.uid, entry.version))
    print("CONTENT {}".format(entry.content))
    print()


def printEntry(entry):
    print("UID {}".format(entry.uid))
    print("CONTENT {}".format(entry.content))
    print()


email = sys.argv[1]
servicePassword = sys.argv[2]
userPassword = sys.argv[3]
remoteUrl = sys.argv[4]

# Token should be saved intead of requested every time
authToken = api.Authenticator(remoteUrl).get_auth_token(email, servicePassword)

etesync = api.EteSync(email, authToken, remote=remoteUrl)
print("Deriving key")
# Very slow operation, should probably be securely cached
etesync.derive_key(userPassword)
print("Syncing")
etesync.sync()
print("Syncing done")

if len(sys.argv) == 6:
    journal = etesync.get(sys.argv[5])

    # Enable if you'd like to dump the journal
    if False:
        for entry in journal.list():
            printEntry(entry)

    # Or interact with the collection
    print("Journal items: {}".format(len(list(journal.list()))))
    print("Collection items: {}".format(len(list(journal.collection.list()))))
    print("Collection: {}".format(list(journal.collection.list())))
else:
    for entry in etesync.list():
        printJournal(entry)
