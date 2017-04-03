import pytest
import binascii
import requests
import json

import etesync as api
from etesync import exceptions
from etesync.crypto import hmac256


USER_EMAIL = 'test@localhost'
USER_PASSWORD = 'SomePassword'
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

        etesync.sync()

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

        ev = api.Event.create(a, '2cd64f22-1111-44f5-bc45-53440af38cec',
                              'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:+//Yo\r\nBEGIN:VEVENT\r\nDTSTAMP:20170324T164' +
                              '747Z\r\nUID:2cd64f22-1111-44f5-bc45-53440af38cec\r\nDTSTART;VALUE\u003dDATE:20170324' +
                              '\r\nDTEND;VALUE\u003dDATE:20170325\r\nSUMMARY:Feed cat\r\nSTATUS:CONFIRMED\r\nTRANSP:' +
                              'TRANSPARENT\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n')
        ev.save()

        etesync.sync()
        ev = a.get(ev.uid)

        assert len(list(a.journal.list())) == 1
        assert get_action(list(a.journal.list())[-1]) == 'ADD'

        ev.content = ev.content + b' '
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
