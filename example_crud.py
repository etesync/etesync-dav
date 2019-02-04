#!/usr/bin/env python

import etesync as api

# The EtesyncCRUD class exposes methods for each of the CRUD operations
# (Create, Retrieve, Update and Delete) and for sync with the server.
# It handles only one calendar

# The class is initialized with user details, authToken and
# EITHER the encryption password OR the cipher key.

# Intended usage is that a calling program (a CLI) obtains user credentials
# from terminal input or some secure storage (like a key ring)
# and then creates an instance of EtesyncCRUD as follows:

# # call with cipher key
# crud = EtesyncCRUD(email, None, remoteUrl, uid, authToken, cipher_key)
# # call with encryption password
# crud = EtesyncCRUD(email, userPassword, remoteUrl, uid, authToken, None)

# The CLI program can then perform CRUD operations by calling
# crud.create_event, crud.retrieve_event,
# crud.update_event and crud.delete_event

# The CLI must explicitly call crud.sync when needed. For example:
# (a) if the server has been updated from another device
# (b) after any CRUD operation other than Retrieve

# No exception handling is done. That is left to the CLI.


class EtesyncCRUD:
    def __init__(self, email, userPassword, remoteUrl, uid, authToken,
                 cipher_key=None):
        """Initialize

        Parameters
        ----------
        email : etesync username(email)
        userPassword : etesync encryption password
        remoteUrl : url of etesync server
        uid : uid of calendar
        authToken : authentication token for etesync server
        """
        self.etesync = api.EteSync(email, authToken, remote=remoteUrl)
        if cipher_key:
            self.etesync.cipher_key = cipher_key
        else:
            self.etesync.derive_key(userPassword)
        self.journal = self.etesync.get(uid)
        self.calendar = self.journal.collection

    def create_event(self, event):
        """Create event

        Parameters
        ----------
        event : iCalendar file as a string
        (calendar containing one event to be added)
        """
        ev = api.Event.create(self.journal.collection, event)
        ev.save()

    def update_event(self, event, uid):
        """Edit event

        Parameters
        ----------
        event : iCalendar file as a string
        (calendar containing one event to be updated)
        uid : uid of event to be updated
        """
        ev_for_change = self.calendar.get(uid)
        ev_for_change.content = event
        ev_for_change.save()

    def retrieve_event(self, uid):
        r"""Retrieve event by uid

        Parameters
        ----------
        uid : uid of event to be retrieved

        Returns
        -------
        iCalendar file (as a string)
        """
        return self.calendar.get(uid).content


    def all_events(self):
        """Retrieve all events in calendar

        Returns
        -------
        List of iCalendar files (as strings)
        """
        return [e.content for e in self.calendar.list()]

    def delete_event(self, uid):
        """Delete event and sync calendar

        Parameters
        ----------
        uid : uid of event to be deleted
        """
        ev_for_deletion = self.calendar.get(uid)
        ev_for_deletion.delete()

    def sync(self):
        r"""Sync with server
        """
        self.etesync.sync()
