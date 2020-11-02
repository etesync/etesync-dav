## Outlook

Outlook doesn't natively support CalDAV and CardDAV and requires an open-source 3rd party extension called [CalDAV synchronizer](https://caldavsynchronizer.org/).

1. Install CalDAV synchronizer from this link: https://caldavsynchronizer.org/download-2/
2. Open a browser and go to http://localhost:37358. Log in to your EteSync DAV Management. Identify the e-mail address corresponding to the calendar you want to sync and click the green “Copy Password” button to its right.
3. Open Outlook. There should be a menu item called CalDav Synchronizer in the menu along the top. Click that menu item.
4. Click Synchronization Profiles. You need to add two profiles: one for calendar, one for contacts. Let’s start with calendar.
5. Click the green + top-right and from the screen with available profile types select “Generic CalDav/CardDav”.
6. Complete the new profile form as follows:
  - Name: A friendly name for your EteSync calendar – for instance EteSync Calendar.
  - Outlook folder: From the dropdown, pick or make (with the New button) the Outlook folder where you want the EteSync calendar items to be stored. The default local calendar folder is Outlook/Calendar, but you could create a subfolder like Outlook/Calendar/EteSync Calendar.
  - Tick “Synchronize items immediately after change”.
  - DAV URL: http://localhost:37358/
  - Username: your account's username.
  - Password: paste the password you copied in step 2
  - Email address: same as Username
7. Click OK at the bottom of the profile form.
8. Repeat steps 4 to 7 to add a profile for your contacts – for instance EteSync Contacts. The default local contacts folder is Outlook/Contacts, but you could create a subfolder like Outlook/Contacts/EteSync Contacts.


## Windows Calendar and Windows People

While EteSync-DAV works great on Windows 10, due to bugs in Windows itself, the instructions require a few extra steps for syncing with Windows Calendar and Windows people. Other clients, such as Thunderbird and Outlook, do not require these extra steps.

### Setup SSL

Windows 10 clients (e.g. Windows Calendar and People) fail without an error when the DAV server doesn't use SSL, so we need to enable SSL for etesync-dav.

Instructions differ depending on how you run `etesync-dav`. Most people will just need the first.

#### Webui

1. Login
2. Click on the "Setup SSL" button at the top and wait.
3. Click "yes" in the popup to approve installing your newly generated SSL certiifcate.
4. Restart `etesync-dav`

#### Command line tool

1. Login
2. Run `etesync-dav certgen`
3. Enter your password once prompted by the system.
4. Restart `etesync-dav`

### Configuration

Windows 10 supports CalDAV and CardDAV account, though for whatever reason, they don't have an easy UI to enable them, so they need to be added in an awkward manner.

This works for Windows Calendar and People, though apparently Outlook has a different way of adding caldav accounts.

1. Open the windows settings app (search for "Settings" in the start menu's search box)
2. Go to Email & accounts and click add account
3. Choose iCloud and put in your username and for the password use "NotPassword". Click save.
4. From the account list click on your account and then click modify
5. Scroll to the bottom and tap on "Advanced mailbox settings"
6. For SMTP/IMAP put `localhost` as the server. Make sure to also set email fetch frequency to manual, and disable email sync if not already disabled.
7. Scroll down to the caldav and carddav servers and put `https://localhost:37358`. Please note it's https, not http.
8. Put in your real password and click save.
9. Windows should now sync your account. The initial sync may take a bit of time, so wait for a bit.
9. Give the initial sync some time, windows takes its time before
