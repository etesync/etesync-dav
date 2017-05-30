import pytest

from etesync import crypto, exceptions


USER_EMAIL = 'test@localhost'
USER_PASSWORD = 'SomePassword'
TEST_REMOTE = 'http://localhost:8000'
TEST_DB = ':memory:'

# Derived key
DERIVED_KEY = (b'\x1a\x99\xfa\x8f\xa5\x89\xff\xd2ImY\x16\x86a\x1ff9jJ\x9b9\xaf\x01\x0e\xce5\x0e;J\xea\xb9\xfb' +
               b'\xdb\xe2\xfbS\xe1G\xd1\x83\x1d.2+\xee\x1b\x08\xc5\xef\xff\x18\xd7=`\x94\x80\x12_\xb3\xb3\xff' +
               b'\x89v\x8e\xe7 \x7f\xe9@\xce\r\xa8M\x91hui\x17E\x90\x83\x98V\xbbs\xd6\xbc\xffN1"\xce\xe4\xa0Y' +
               b'\x94\x1f~\x11\x97\xd5\xd7[\xa5v\xfc`\xd5\x8a\x04!AO.Zz\xc6\xa3\xbfy\xb6\xeah5\x03\x1b\xb4\x1f' +
               b'\x11\x80\xc5\xf9\x1b+\xb1G\x9eE\xbd\xcc\x9b\x1e\x96\x01o\n\xc3"\xc2\xaf]\xc0qXQ,q\xd3T\xf3<\x9e' +
               b'\xab|\xa3\xbc:?[\xfc\xb6\xe1\xd0)[y\xa76\x8e\xef\xb3\n\x0b\xda\xbadf=\xdd\xab')


class TestCrypto:
    @pytest.mark.skip(reason='Too slow to always test.')
    def test_derive(self):
        # Just make sure we don't break derivation
        key = crypto.derive_key(USER_PASSWORD, USER_EMAIL)
        assert key == DERIVED_KEY

    def test_crypto_v1(self):
        # Just make sure we don't break derivation
        crypto_manager = crypto.CryptoManager(1, DERIVED_KEY, b'TestSaltShouldBeJournalId')
        clear_text = b'This Is Some Test Cleartext.'
        cipher = crypto_manager.encrypt(clear_text)
        assert clear_text == crypto_manager.decrypt(cipher)

        expected = b'/?\x87P\\\xe1\xd4wc\xc6\xe1\x9dB\xb0p\x04mH\xcct\xf4\xba\x0e\xa6;\xc7\xf0x\xf4\x9b^\xd7'
        assert expected == crypto_manager.hmac(b'Some test data')

    def test_crypto_v2(self):
        # Just make sure we don't break derivation
        crypto_manager = crypto.CryptoManager(2, DERIVED_KEY, b'TestSaltShouldBeJournalId')
        clear_text = b'This Is Some Test Cleartext.'
        cipher = crypto_manager.encrypt(clear_text)
        assert clear_text == crypto_manager.decrypt(cipher)

        expected = (b']\x0f\xc0\xd2\x07\xa7\xb4\xe6\x84\xf7\xc4}\xc37\xf7\xccB\x00\x1e>\x0e\x1fQ\x85\xf0\x9e\x02\xe8' +
                    b'\x98\x89\xba\x9a')
        assert expected == crypto_manager.hmac(b'Some test data')

    def test_asymmetric_crypto(self):
        key_pair = crypto.AsymmetricCryptoManager.generate_key_pair()
        asymmetric_crypto_manager = crypto.AsymmetricCryptoManager(key_pair)
        encrypted_key = asymmetric_crypto_manager.encrypt(key_pair.public_key, DERIVED_KEY)
        decrypted_key = asymmetric_crypto_manager.decrypt(encrypted_key)

        assert DERIVED_KEY == decrypted_key

        crypto_manager = crypto.CryptoManager(2, DERIVED_KEY, b'TestSaltShouldBeJournalId')
        clear_text = b'This Is Some Test Cleartext.'
        cipher = (b'\x109\xc3_\x1dM\xcd\xcf\x0e>_\xcb\x10\xff7\x07\xe3\xc6/\x17Y\x94} \x04\x1f\x11g\xa3\x1e\x11\xe5' +
                  b'\xfe#\xbb]JZm\x1dk\xb2\x97\xde\xfcdo\xd3')
        assert clear_text == crypto_manager.decrypt(cipher)

    def test_crypto_v_too_new(self):
        with pytest.raises(exceptions.VersionTooNew):
            crypto.CryptoManager(293, DERIVED_KEY, b'TestSalt')
