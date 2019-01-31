import pytest
import binascii
import requests

import etesync as api
from etesync import exceptions
from etesync.crypto import hmac256

# Not public API, used for verification
from etesync.service import EntryManager, RawJournal, CryptoManager


USER_EMAIL = 'test@localhost'
USER_PASSWORD = 'SomePassword'
TEST_REMOTE = 'http://localhost:8000/'
TEST_DB = ':memory:'


# Gets fake (consistent between tests) random numbers
def get_random_uid(context):
    context._rand = getattr(context, '_rand', 0)
    context._rand = context._rand + 1
    return binascii.hexlify(hmac256(b'', str(context._rand).encode())).decode()


@pytest.fixture(scope="module")
def etesync():
    auth = api.Authenticator(TEST_REMOTE)
    token = auth.get_auth_token(USER_EMAIL, USER_PASSWORD)
    return api.EteSync(USER_EMAIL, token, remote=TEST_REMOTE, db_path=TEST_DB)


class TestCollection:
    @pytest.fixture(autouse=True)
    def transact(self, request, etesync):
        # Clear the db for this user
        headers = {'Authorization': 'Token ' + etesync.auth_token}
        response = requests.post(TEST_REMOTE + 'reset/', headers=headers, allow_redirects=False)
        assert response.status_code == 200
        etesync._init_db(TEST_DB)
        yield

    def test_crud(self, etesync):
        # Empty collections
        assert len(list(etesync.list())) == 0

        # Create
        a = api.Calendar.create(etesync, get_random_uid(self), {'displayName': 'Test', 'description': 'Test desc'})
        b = api.AddressBook.create(etesync, get_random_uid(self), {'displayName': 'Test 2'})
        assert a is not None
        assert b is not None

        # Description is what we expect
        assert a.description == 'Test desc'

        # Still empty because we haven't saved
        assert len(list(etesync.list())) == 0

        # Fetch before saved:
        with pytest.raises(exceptions.DoesNotExist):
            etesync.get(a.journal.uid)

        a.save()
        assert 'Test' == list(etesync.list())[0].collection.display_name
        assert len(list(etesync.list())) == 1
        b.save()
        assert len(list(etesync.list())) == 2

        # Get
        assert a.journal.uid == etesync.get(a.journal.uid).uid
        assert b.journal.uid == etesync.get(b.journal.uid).uid

        # Check version is correct
        assert a.journal.version > 0

        # Delete
        a.delete()
        assert len(list(etesync.list())) == 1
        b.delete()
        assert len(list(etesync.list())) == 0

        # Try saving two collections with the same uid
        c = api.Calendar.create(etesync, a.journal.uid, {'displayName': 'Test'})
        with pytest.raises(exceptions.AlreadyExists):
            c.save()

    def test_content_crud(self, etesync):
        a = api.Calendar.create(etesync, get_random_uid(self), {'displayName': 'Test'})
        b = api.AddressBook.create(etesync, get_random_uid(self), {'displayName': 'Test 2'})
        c = api.Calendar.create(etesync, get_random_uid(self), {'displayName': 'Test 3'})

        ev = api.Event.create(a,
                              'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:+//Yo\r\nBEGIN:VEVENT\r\nDTSTAMP:20170324T164' +
                              '747Z\r\nUID:2cd64f22-1111-44f5-bc45-53440af38cec\r\nDTSTART;VALUE\u003dDATE:20170324' +
                              '\r\nDTEND;VALUE\u003dDATE:20170325\r\nSUMMARY:Feed cat\r\nSTATUS:CONFIRMED\r\nTRANSP:' +
                              'TRANSPARENT\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n')

        # Try saving before the journal is saved
        with pytest.raises(exceptions.DoesNotExist):
            ev.save()

        # Create the event
        a.save()
        ev.save()

        assert ev.uid == a.get('2cd64f22-1111-44f5-bc45-53440af38cec').uid

        # Fail to create another event with the same uid
        ev = api.Event.create(a,
                              'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:+//Yo\r\nBEGIN:VEVENT\r\nDTSTAMP:20170324T164' +
                              '747Z\r\nUID:2cd64f22-1111-44f5-bc45-53440af38cec\r\nDTSTART;VALUE\u003dDATE:20170324' +
                              '\r\nDTEND;VALUE\u003dDATE:20170325\r\nSUMMARY:Feed cat\r\nSTATUS:CONFIRMED\r\nTRANSP:' +
                              'TRANSPARENT\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n')
        with pytest.raises(exceptions.AlreadyExists):
            ev.save()

        # Trying to add an Event into an AddressBook
        b.save()

        # Wrong child in collection
        with pytest.raises(exceptions.TypeMismatch):
            api.Event.create(b, (
                  'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:+//Yo\r\nBEGIN:VEVENT\r\nDTSTAMP:20170324T164' +
                  '747Z\r\nUID:2cd64f22-2222-44f5-bc45-53440af38cec\r\nDTSTART;VALUE\u003dDATE:20170324' +
                  '\r\nDTEND;VALUE\u003dDATE:20170325\r\nSUMMARY:Feed cat\r\nSTATUS:CONFIRMED\r\nTRANSP:' +
                  'TRANSPARENT\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n'))

        # Same uid in different collections
        c.save()
        ev2 = api.Event.create(c, ev.content)
        ev2.save()

        # Check it's actually there
        assert len(list(c.list())) == 1

        # # First is still here even after we delete the new one
        ev2.delete()
        assert len(list(c.list())) == 0

        assert ev.uid == a.get('2cd64f22-1111-44f5-bc45-53440af38cec').uid

        # Check fetching a non-existent item
        with pytest.raises(exceptions.DoesNotExist):
            c.get('bla')

    def test_syncing(self, etesync):
        a = api.Calendar.create(etesync, get_random_uid(self), {'displayName': 'Test'})

        ev = api.Event.create(a,
                              'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:+//Yo\r\nBEGIN:VEVENT\r\nDTSTAMP:20170324T164' +
                              '747Z\r\nUID:2cd64f22-1111-44f5-bc45-53440af38cec\r\nDTSTART;VALUE\u003dDATE:20170324' +
                              '\r\nDTEND;VALUE\u003dDATE:20170325\r\nSUMMARY:Feed cat\r\nSTATUS:CONFIRMED\r\nTRANSP:' +
                              'TRANSPARENT\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n')

        # Create the event
        a.save()
        ev.save()

        # Add another and then sync (check we can sync more than one)
        ev = api.Event.create(a,
                              'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:+//Yo\r\nBEGIN:VEVENT\r\nDTSTAMP:20170324T164' +
                              '747Z\r\nUID:2cd64f22-1111-44f5-bc45-aaaaaaaaaaac\r\nDTSTART;VALUE\u003dDATE:20170324' +
                              '\r\nDTEND;VALUE\u003dDATE:20170325\r\nSUMMARY:Feed 2\r\nSTATUS:CONFIRMED\r\nTRANSP:' +
                              'TRANSPARENT\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n')
        ev.save()

        assert len(list(a.list())) == 2

        etesync.sync()

        ev.delete()
        assert len(list(a.list())) == 1

        etesync.sync()

        # Verify we created valid journal entries
        journal_uid = a.journal.uid
        manager = EntryManager(etesync.remote, etesync.auth_token, journal_uid)

        crypto_manager = CryptoManager(a.journal.version, etesync.cipher_key, journal_uid.encode())
        journal = RawJournal(crypto_manager, uid=journal_uid)
        crypto_manager = etesync._get_journal_cryptomanager(journal)

        prev = None
        last_uid = None

        for entry in manager.list(crypto_manager, last_uid):
            entry.verify(prev)

            prev = entry

    def test_unicode(self, etesync):
        a = api.Calendar.create(etesync, get_random_uid(self), {'displayName': 'יוניקוד'})

        # Create the event
        a.save()

        a2 = etesync.get(a.journal.uid)

        assert a.display_name == a2.collection.display_name

        ev = api.Event.create(a, (
              'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:+//Yo\r\nBEGIN:VEVENT\r\nDTSTAMP:20170324T164' +
              '747Z\r\nUID:2cd64f22-2222-44f5-bc45-53440af38cec\r\nDTSTART;VALUE\u003dDATE:20170324' +
              '\r\nDTEND;VALUE\u003dDATE:20170325\r\nSUMMARY:יוניקוד\r\nSTATUS:CONFIRMED\r\nTRANSP:' +
              'TRANSPARENT\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n'))

        ev.save()

        assert ev.content == a.get(ev.uid).content

        # Test repr works
        repr(ev)
