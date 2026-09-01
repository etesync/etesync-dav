from contextlib import contextmanager
from unittest import TestCase, mock

from etebase import etebase_python

from etesync_dav.local_cache import Etebase
from etesync_dav.radicale.etesync_cache import EteSyncCache
from etesync_dav.radicale.storage import SyncThread


class TokenRefreshTest(TestCase):
    def test_refreshes_and_persists_etebase_session(self):
        cache = EteSyncCache("unused-creds", "unused-db")
        cache.creds = mock.Mock()
        cache.creds.get_server_url.return_value = "https://example.com/"

        etesync = Etebase.__new__(Etebase)
        etesync.etebase = mock.Mock()
        etesync.stored_session = "old-stored-session"
        etesync.etebase.save.return_value = "new-stored-session"
        cache.etesync_for_user = mock.Mock(return_value=(etesync, False))

        self.assertTrue(cache.refresh_etebase_token("alice"))

        etesync.etebase.fetch_token.assert_called_once_with()
        etesync.etebase.save.assert_called_once_with(None)
        cache.creds.set_etebase.assert_called_once_with("alice", "new-stored-session", "https://example.com/")
        cache.creds.save.assert_called_once_with()
        self.assertEqual(etesync.stored_session, "new-stored-session")

    def test_does_not_refresh_legacy_session(self):
        cache = EteSyncCache("unused-creds", "unused-db")
        cache.etesync_for_user = mock.Mock(return_value=(object(), False))

        self.assertFalse(cache.refresh_etebase_token("alice"))

    @mock.patch("etesync_dav.radicale.storage.refresh_etebase_token", return_value=True)
    @mock.patch("etesync_dav.radicale.storage.etesync_for_user")
    def test_sync_retries_after_refreshing_invalid_token(self, etesync_for_user_mock, refresh_mock):
        etesync = mock.Mock()
        etesync.sync.side_effect = [etebase_python.Error("Invalid token."), None]

        @contextmanager
        def context():
            yield etesync, False

        etesync_for_user_mock.return_value = context()

        SyncThread("alice").sync_once()

        refresh_mock.assert_called_once_with("alice")
        self.assertEqual(etesync.sync.call_count, 2)

    @mock.patch("etesync_dav.radicale.storage.refresh_etebase_token")
    @mock.patch("etesync_dav.radicale.storage.etesync_for_user")
    def test_sync_does_not_refresh_other_etebase_errors(self, etesync_for_user_mock, refresh_mock):
        etesync = mock.Mock()
        etesync.sync.side_effect = etebase_python.Error("Invalid stoken.")

        @contextmanager
        def context():
            yield etesync, False

        etesync_for_user_mock.return_value = context()

        with self.assertRaisesRegex(etebase_python.Error, "Invalid stoken"):
            SyncThread("alice").sync_once()

        refresh_mock.assert_not_called()
