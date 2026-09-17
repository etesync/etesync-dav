import unittest
from unittest.mock import patch

from etesync_dav import config


class LocalServerURLTests(unittest.TestCase):
    def test_uses_configured_port(self):
        with patch.object(config, "SERVER_HOSTS", "localhost:8080"):
            self.assertEqual(config.local_server_url("http"), "http://localhost:8080")

    def test_replaces_wildcard_host(self):
        with patch.object(config, "SERVER_HOSTS", "0.0.0.0:37358,[::]:37358"):
            self.assertEqual(config.local_server_url("https"), "https://localhost:37358")

    def test_formats_ipv6_host(self):
        with patch.object(config, "SERVER_HOSTS", "[::1]:8080"):
            self.assertEqual(config.local_server_url("http"), "http://[::1]:8080")


if __name__ == "__main__":
    unittest.main()
