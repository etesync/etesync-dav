# A Sandboxing Systemd Unit For Etesync-dav
This is an example systemd unit file that installs and start etesync-dav.
You will want to adapt it to your use case.

To use etesync-dav via this unit you need to:
* generate the credential files and configuration for Radicale
* install the unit
* start the unit
* [connect your client to etesync](https://github.com/etesync/etesync-dav)

## FAQ
### How should I generate the credential files and Radicale configuration?

For each user ($USER is the user name of the remote etesync server) run the following (replace `etesync.example.org` with the URL of your server or remove it if you use the official EteSync server):
`sudo systemd-run --pty -p DynamicUser=true -p DevicePolicy=closed -p CapabilityBoundingSet= -p NoNewPrivileges=true -p PrivateDevices=true -p 'RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6' -p ProtectHome=true -p ProtectSystem=strict -p InaccessiblePaths=/boot -E HOME=/tmp -p WorkingDirectory=/tmp -E ETESYNC_URL=https://etesync.example.org sh -c "pip3 install etesync-dav && .local/bin/etesync-dav-manage add $USER && echo >> .config/etesync-dav/etesync_creds && .local/bin/etesync-dav -H localhost:234; more .config/etesync-dav/* | cat "`

It is normal see an error message `ERROR: An exception occurred during server startup: Failed to start server 'localhost:234': [Errno 13] Permission denied`.

At the end of the `systemd-run`, `more` will show the contents of three files.  The contents should be pasted into files in `~/.config/etesync-dav`.

### How can I install this unit?
Symlink it to `/etc/systemd/system/etesync-dav@.service`
and then run `sudo systemctl daemon-reload`.

### How do I start this unit?
For each user run `sudo systemctl enable etesync-dav@$USER` and `sudo systemctl start etesync-dav@$USER`.

### Can this unit handle multiple users on the same host?
Yes but each user will need a different port number in the `server`
section of their `~/.config/etesync-dav/radicale.conf`.

### How can I see the unit's logs?
`journalctl -f -u etesync-dav@$USER`

### Why does it install etesync-dav?
This unit installs etesync-dav
because etesync-dav is not available in Debian and somebody has to do the install.
This keeps the starting and installation in one place and means that only the latest version of etesync-dav is ever started.

### Why all the sandboxing systemd parameters?
This unit installs many possibly untrusted dependencies.
The sandboxing means that evil code does not have access to your files.
Evil code can however steal your etesync password also well as stealing
or modifying you calendar and contacts.

### What about limiting network usage?
This will be possible once
[Add support for systemd socket activation](https://github.com/Kozea/Radicale/commit/2275ba4f9323e87eeac61f8811a4cc2773061e70)
is available in etesync-dav.
At that point a systemd socket file will open the network connection on localhost
and etesync-dav can be limited to public IP address and the local DNS server.

### Is there a race at startup?
Yes as systemd thinks that the service is ready before it has opened its socket.
This will be fixed by using a systemd socket unit.

### What about stopping evil code from bitcoin mining?
Perhaps CPUQuota should be reduced but this would slow down startup.

### Why are the pip modules downloaded after every reboot?
It does not seem worth the effort to find a place to keep them.

### Why is the etesync cache lost on reboot?
The data in the cache is not encrypted so it should only be saved to a encrypted disk.
Fxixing this is a future project.

### Is it a security risk that the etesync database is lost on reboot?
Yes as the check for an evil server rewinding the database is lost.

### Why is `MemoryDenyWriteExecute` not set?
It causes SSL verification to fail.

### What version of systemd does the unit work with?
Systemd is a moving target, at the moment this unit is tested with 239, more recent version should work as well

### Why install etesync-dav in /tmp rather than the run directory?
The `/run` filesystem is mounted `noexec` and `pip3` `.so` libraries cannot be used when they are
on a filesystem mounted `noexec`.

### Can I increase the logging?
Yes, use `sudo systemctl edit etesync-dav@$USER` to add `Environment=EYESYNC_DAV_ARGS=--debug` in the `[Service]` section.

### Can I stop the messages from `pip3`?
Yes, use `sudo systemctl edit etesync-dav@$USER` to add `Environment=PIP_ARGS=--quiet` in the `[Service]` section.

### How can I get this unit to start after my encrypted home directory is available?
Use `sudo systemctl edit etesync-dav@$USER` to add something like
```
[Install]
WantedBy=
WantedBy=home-%i.mount
```
