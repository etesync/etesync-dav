======================
Startup file for macOS
======================

`com.etesync.etesync-dav.plist` is an "agent configuration file" for
macOS' `launchd`. (See the manual pages for `launchd`, `launchd.plist`,
and `launchctl` for details.)

You should place this file in:

    ~/Library/LaunchAgents

After doing so, `etesync-dav` will start automatically when you log in.
Also, you can start and stop it via `launchctl`.