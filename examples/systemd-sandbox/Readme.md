# A Sandboxing Systemd Unit For Etesync-dav
This is an example systemd unit file that installs and start etesync-dav.
You will want to adapt it to your use case.


To use etesync-dav via this unit you need to:
* install the unit

* start the unit

* create your local user with the [management UI](http://localhost:37358)

## FAQ
### How should I generate the credential files and Radicale configuration?

Create your local user with [management UI](http://localhost:37358) as described in the
[readme](https://github.com/etesync/etesync-dav/blob/master/README.md#configuration-and-running)

### How can I install this unit?
Symlink it to `/etc/systemd/system/etesync-dav@.service`
and then run `sudo systemctl daemon-reload`.

### How do I start this unit?
For each user run `sudo systemctl enable etesync-dav@$USER` and `sudo systemctl start etesync-dav@$USER`.

### Can this unit handle multiple users on the same host?
Yes but each user will need to use a different port by setting ETESYNC_LISTEN_PORT using
`sudo systemctl edit etesync-dav@$USER` to create
```
[Service]
Environment=ETESYNC_LISTEN_PORT=45625
```

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

### Are the pip modules downloaded after every reboot?
No they are cached and should be automatically cleaned.

### Why is `MemoryDenyWriteExecute` not set?
It causes SSL verification to fail.

### Is the etesync cache lost on reboot?
No, howvever if your /var/cache is not on an encrypted disk, considering using
`sudo systemctl edit etesync-dav@`
to move the cache to /run (which is kept in memory).
by adding `Environment=ETESYNC_DATA_DIR=%t/%N/data` with `sudo systemctl edit etesync-dav@`
In this case you should
```
mkdir ~/.local/share/etesync-dav
sudo cp /var/cache/etesync-dav@$USER/data/etesync_creds htpaswd ~/.local/share/etesync-dav/
sudo chown $USER ~/.local/share/etesync-dav/*
```
so that the unit can copy the credentials into the volatile cache after each restart.

### What version of systemd does the unit work with?
Systemd is a moving target, at the moment this unit is tested with 245, more recent version should work as well

### Why install etesync-dav in /tmp rather than the run directory?
The `/run` filesystem is mounted `noexec` and `pip3` `.so` libraries cannot be used when they are
on a filesystem mounted `noexec`.

### Can I increase the logging?
Yes, use `sudo systemctl edit etesync-dav@` to add `Environment=EYESYNC_DAV_ARGS=--debug` in the `[Service]` section.

### Can I stop the messages from `pip3`?
Yes, use `sudo systemctl edit etesync-dav@` to add `Environment=PIP_ARGS=--quiet` in the `[Service]` section.

### How can I get this unit to start after my encrypted home directory is available?
Use `sudo systemctl edit etesync-dav@` to add something like
```
[Install]
WantedBy=
WantedBy=home-%i.mount
```
