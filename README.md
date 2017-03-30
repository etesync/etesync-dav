This is a python module for interaction with EteSync

It was hacked together so other projects would be able to more easily integrate
with EteSync. This means it may change, especially when it comes to naming,
though the main ideas should remain the same.

There is one Authenticator endpoint, and one endpoint for the rest of the API
interactions.

The way it works is that you run "sync", which syncs local cache with server.
Afterwards you can either access the journal directly, or if you prefer,
you can access a collection, for example a Calendar, and interact with the
entries themselves, which are already in sync with the journal.

Check out [example.py](example.py) for a usage example.
