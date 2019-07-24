## Configuration

* OSX
    * CalDAV: Works. Setup instructions:
      * Internet Accounts->Add Other Account->CalDAV account
      * Account Type: Advanced
      * Username: user@example.com
      * Password: generated etesync-dav password
      * Server Address: localhost
      * Server Path: /
      * Port: 37358
      * Prior to macOS Mojave: Uncheck "Use SSL".
        From macOS Mojave onwards: Check "Use SSL."
        (Mojave require SSL to be enabled.)
    * CardDAV: Works. Setup instructions:
      * Internet Accounts->Add Other Account->CardDAV account
      * Account Type: Manual
      * Username: user@example.com
      * Password: generated etesync-dav password
      * Server Address: `http://localhost:37358/` (under macOS Mojave: `https://localhost:37358/`)

## macOS Mojave

macOS Mojave enforces the use of SSL, *regardless* of whether you enable the
checkbox for SSL or not. So to use EteSync, you have to enable SSL.

You can do so by either using the `etesync-dav-certgen` utility, or follow
the instructions below. Following these instructions will generate a self-signed SSL certificate,
configure etesync-dav to use that certificate, and make your system trust it.

### Automatic SSL setup

You can automatically setup SSL by running the following command:

    etesync-dav-certgen --trust-cert

You will be prompted for your login password. This is because `--trust-cert`
imports the certificate into your login keychain and then instructs the
system to trust it for SSL connections.

Once you have run `etesync-dav-certgen`, you need to restart `etesync-dav`
for the changes to take effect. Then proceed to configure CalDAV and CardDAV
as described above.

If you have already configured `etesync-dav` to use SSL, 
`etesync-dav-certgen` will use your existing settings; in won't
reconfigure `etesync-dav`. It also won't overwrite existing
certificates. `--trust-cert` works on macOS 10.3 or newer only.
See `etesync-dav-certgen --help` for details.

### Manual SSL setup

Alternatively you can generate and configure a self-signed certificate manually with the following steps:

1. Generate a self-signed certificate (valid for 10 years)

````bash
cd ~/Library/Application\ Support/etesync-dav
openssl req -new -newkey rsa:4096 -days 3650 -nodes -x509 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=etesync.localhost" -keyout etesync.key -out etesync.crt
````
    
2. Using `open` command triggers macOS "add to keychain" dialog (equivelent of double-clicking that file in Finder):

````bash
open etesync.crt
````
    
3. In the dialog confirm adding to "login" keychain.
4. Open `Keychain Access` app, find and open `etesync.localhost` (under Keychains: login, Category: Certificates), expand "Trust" and pick "Always trust" for SSL. 
5. Edit `~/Library/Application Support/etesync-dav/radicale.conf`, under `[server]` enter the following to make it use the certificate:

````ini
    ssl = yes
    certificate = ~/Library/Application Support/etesync-dav/etesync.crt
    key = ~/Library/Application Support/etesync-dav/etesync.key
````

6. Restart `etesync-dav`

### SSL in non-macOS applications

Some applications, above all, web browers (Firefox, Chrome, ...) manage certificates themselves, rather than relying on the mechanisms the operating system provides. But `etesync-dav-certgen` and the instructions above only make the operating system trust the self-signed certificate. If you want to use SSL to connect to `etesync-dav` using such applications, you need to make them trust the self-signed certificate.

