This is an [EteSync](https://www.etesync.com) storage plugin for [Radicale](http://radicale.org/).

This plugin makes Radicale use EteSync as the storage module, essentially
making Radicale a CalDav/CardDav frontend for EteSync.

For all I can tell, everything works as expected, with the exception of
Last-Modified which is not yet implemented and just returns the modification
date as "now" (not the end of the world as etag is implemented correctly).

# Installation

`pip install radicale radicale_storage_etesync`

# Configuration

This plugin assumes only authenticated users are allowed to connect to Radicale,
so make sure to correctly set the Radicale `auth` backend accordingly.
Please refer to the [Radicale docs](http://radicale.org/configuration/#auth) for more information.

You also need to set the storage type to `radicale_storage_etesync`, and
populate the `etesync_storage` section.

Example config:

```
[server]
hosts = localhost:5232

[storage]
type = radicale_storage_etesync

[auth]
type = htpasswd
htpasswd_filename = ./htpaswd
htpasswd_encryption = plain

[etesync_storage]
database_filename = ./etesyncache.db
remote_url = https://api.etesync.com/
credentials_filename = ./etesync_creds
```

In addition to the Radicale config above, you need to have a credentials file
at the path specified above that includes the authentication token and the
base64 encoded cipher key per allowed user.

Example credentials file:

```json
{
   "users": {
        "me@etesync.com": {
             "authToken": "c5d796ad113f596bde14c45e5888919f8b4f307a",
             "cipherKey": "ZWFudWhvZXN1bnRoZXN1bnRhb2VodXNudGVvYWh1c25lb3RhaHVzb25lYXR1aGFzb2VudWhhb2VzbnR1aGFlb3N1dGhhZW9zbnR1aAo="
        }
   }
}
```
