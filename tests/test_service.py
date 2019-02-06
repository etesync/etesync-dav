import pytest
import binascii
import requests
import json

import etesync as api
from etesync import exceptions
from etesync.crypto import hmac256

# Not public API, used for verification
from etesync.service import EntryManager, RawJournal, CryptoManager

USER_EMAIL = 'test@localhost'
USER_PASSWORD = 'SomePassword'
USER2_EMAIL = 'test2@localhost'
TEST_REMOTE = 'http://localhost:8000/'
TEST_DB = ':memory:'


# Gets fake (consistent between tests) random numbers
def get_random_uid(context):
    context._rand = getattr(context, '_rand', 0)
    context._rand = context._rand + 1
    return binascii.hexlify(hmac256(b'', str(context._rand).encode())).decode()


def get_action(entry):
    return json.loads(entry._cache_obj.content).get('action')


@pytest.fixture(scope="module")
def etesync():
    auth = api.Authenticator(TEST_REMOTE)
    token = auth.get_auth_token(USER_EMAIL, USER_PASSWORD)
    return api.EteSync(USER_EMAIL, token, remote=TEST_REMOTE, db_path=TEST_DB)


class TestService:
    @pytest.fixture(autouse=True)
    def transact(self, request, etesync):
        # Clear the db for this user
        headers = {'Authorization': 'Token ' + etesync.auth_token}
        response = requests.post(TEST_REMOTE + 'reset/', headers=headers, allow_redirects=False)
        assert response.status_code == 200
        etesync._init_db(TEST_DB)
        yield

    def test_auth_token(self):
        auth = api.Authenticator(TEST_REMOTE)
        token = auth.get_auth_token(USER_EMAIL, USER_PASSWORD)
        assert len(token) > 0

        with pytest.raises(exceptions.UnauthorizedException):
            token = auth.get_auth_token(USER_EMAIL, 'BadPassword')

    def test_sync_simple(self, etesync):
        a = api.Calendar.create(etesync, get_random_uid(self), {'displayName': 'Test'})
        b = api.AddressBook.create(etesync, get_random_uid(self), {'displayName': 'Test 2'})

        a.save()
        b.save()

        assert len(list(etesync.list())) == 2

        # Make sure we detect dirty correctly
        assert etesync.journal_list_is_dirty()
        assert not etesync.journal_is_dirty(a.journal.uid)

        etesync.sync()

        # Make sure they are not dirty anymore
        assert not etesync.journal_list_is_dirty()
        assert not etesync.journal_is_dirty(a.journal.uid)

        # Reset the db
        etesync._init_db(TEST_DB)
        assert len(list(etesync.list())) == 0
        etesync.sync()

        assert len(list(etesync.list())) == 2

        a = etesync.get(a.journal.uid).collection
        b = etesync.get(b.journal.uid).collection
        assert a.display_name == 'Test'

        a.update_info({'displayName': 'Test Update'})
        a.save()
        b.delete()

        etesync.sync()

        with pytest.raises(RuntimeError):
            # Hackily try and update the Journal info's directly
            a.journal.update_info(None)

        # Reset the db
        etesync._init_db(TEST_DB)
        assert len(list(etesync.list())) == 0
        etesync.sync()

        assert len(list(etesync.list())) == 1

        a = etesync.get(a.journal.uid).collection
        assert a.display_name == 'Test Update'

    def test_collection_delete_server(self, etesync):
        a = api.Calendar.create(etesync, get_random_uid(self), {'displayName': 'Test'})
        b = api.AddressBook.create(etesync, get_random_uid(self), {'displayName': 'Test 2'})

        a.save()
        b.save()

        assert len(list(etesync.list())) == 2

        etesync.sync()

        # Reset the db
        prev_db = etesync._database
        etesync._init_db(TEST_DB)
        assert len(list(etesync.list())) == 0
        etesync.sync()

        assert len(list(etesync.list())) == 2

        b.delete()

        etesync.sync()

        # Reset the db
        etesync._set_db(prev_db)
        assert len(list(etesync.list())) == 2
        etesync.sync()

        assert len(list(etesync.list())) == 1

    def test_collection_journal(self, etesync):
        a = api.Calendar.create(etesync, get_random_uid(self), {'displayName': 'Test'})

        a.save()

        assert len(list(etesync.list())) == 1

        # A journal is only dirty if content is dirty
        assert not etesync.journal_is_dirty(a.journal.uid)

        ev = api.Event.create(a,
                              'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:+//Yo\r\nBEGIN:VEVENT\r\nDTSTAMP:20170324T164' +
                              '747Z\r\nUID:2cd64f22-1111-44f5-bc45-53440af38cec\r\nDTSTART;VALUE\u003dDATE:20170324' +
                              '\r\nDTEND;VALUE\u003dDATE:20170325\r\nSUMMARY:FÖÖBÖÖ\r\nSTATUS:CONFIRMED\r\nTRANSP:' +
                              'TRANSPARENT\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n')
        ev.save()

        # We have new content, make sure journal is marked as dirty
        assert etesync.journal_is_dirty(a.journal.uid)

        etesync.sync()

        # We just synced, not dirty anymore.
        assert not etesync.journal_is_dirty(a.journal.uid)

        ev = a.get(ev.uid)

        assert len(list(a.journal.list())) == 1
        assert get_action(list(a.journal.list())[-1]) == 'ADD'

        ev.content = ev.content + ' '
        ev.save()

        etesync.sync()
        ev = a.get(ev.uid)

        assert len(list(a.journal.list())) == 2
        assert get_action(list(a.journal.list())[-1]) == 'CHANGE'

        ev.delete()

        etesync.sync()

        assert len(list(a.journal.list())) == 3
        assert get_action(list(a.journal.list())[-1]) == 'DELETE'

        # Reset db
        etesync._init_db(TEST_DB)
        etesync.sync()

        assert len(list(a.journal.list())) == 3
        assert get_action(list(a.journal.list())[-1]) == 'DELETE'
        assert len(list(a.list())) == 0

    def test_collection_unicode(self, etesync):
        a = api.Calendar.create(etesync, get_random_uid(self), {'displayName': 'fööböö'})
        a.save()

        ev = api.Event.create(
            a,
            ('BEGIN:VCALENDAR\r\n'
             'BEGIN:VEVENT\r\n'
             'UID:test @ foo ät bar град сатану\r\n'
             'SUMMARY:FÖÖBÖÖ\r\n'
             'END:VEVENT\r\n'
             'END:VCALENDAR\r\n')
        )
        ev.save()
        etesync.sync()

    def test_collection_shared(self, etesync):
        from etesync import service, crypto

        a = api.Calendar.create(etesync, get_random_uid(self), {'displayName': 'fööböö'})
        a.save()

        ev = api.Event.create(
            a,
            ('BEGIN:VCALENDAR\r\n'
             'BEGIN:VEVENT\r\n'
             'UID:test @ foo ät bar град сатану\r\n'
             'SUMMARY:FÖÖBÖÖ\r\n'
             'END:VEVENT\r\n'
             'END:VCALENDAR\r\n')
        )
        ev.save()
        journal_manager = service.JournalManager(etesync.remote, etesync.auth_token)
        etesync.sync()

        # Second user
        auth = api.Authenticator(TEST_REMOTE)
        token = auth.get_auth_token(USER2_EMAIL, USER_PASSWORD)
        etesync2 = api.EteSync(USER2_EMAIL, token, remote=TEST_REMOTE, db_path=TEST_DB)
        headers = {'Authorization': 'Token ' + etesync2.auth_token}
        response = requests.post(TEST_REMOTE + 'reset/', headers=headers, allow_redirects=False)
        assert response.status_code == 200

        user_info = etesync2.get_or_create_user_info()
        key_pair = crypto.AsymmetricKeyPair(user_info.content, user_info.pubkey)
        asymmetric_crypto_manager = crypto.AsymmetricCryptoManager(key_pair)
        cipher_key = hmac256(a.journal.uid.encode(), etesync.cipher_key)
        encrypted_key = asymmetric_crypto_manager.encrypt(key_pair.public_key, cipher_key)

        member = service.Member(USER2_EMAIL, encrypted_key)
        journal_manager.member_add(a.journal._cache_obj, member)

        etesync2.sync()

        journal_list = list(etesync2.list())
        assert len(journal_list) == 1

        assert journal_list[0].uid == a.journal.uid

    def test_user_info_manage(self, etesync):
        # FIXME: Shouldn't expose and rely on service
        from etesync import service
        from etesync.crypto import CryptoManager, CURRENT_VERSION

        # Failed get
        info_manager = service.UserInfoManager(etesync.remote, etesync.auth_token)
        with pytest.raises(exceptions.HttpException):
            info_manager.get(USER_EMAIL, etesync.cipher_key)

        # Add
        crypto_manager = CryptoManager(CURRENT_VERSION, etesync.cipher_key, b"userInfo")
        user_info = service.RawUserInfo(crypto_manager, USER_EMAIL, b"pubkeyTest")
        user_info.update(b"contentTest")
        user_info.verify()

        info_manager.add(user_info)

        user_info2 = info_manager.get(USER_EMAIL, etesync.cipher_key)
        user_info2.verify()

        assert user_info.content == user_info2.content
        assert user_info.pubkey == user_info2.pubkey
        assert user_info.owner == user_info2.owner

        # Update
        user_info.update(b"contentTest2")
        info_manager.update(user_info)

        user_info2 = info_manager.get(USER_EMAIL, etesync.cipher_key)
        user_info2.verify()

        assert user_info.content == user_info2.content
        assert user_info.pubkey == user_info2.pubkey
        assert user_info.owner == user_info2.owner

        # Delete
        info_manager.delete(user_info)
        with pytest.raises(exceptions.HttpException):
            info_manager.get(USER_EMAIL, etesync.cipher_key)

    def test_collection_sync(self, etesync):
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
