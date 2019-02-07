from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes, padding
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import os
import hashlib
import hmac

try:
    import scrypt

    def derive_key(user_password, salt):
        return scrypt.hash(password=user_password.encode(),
                           salt=salt.encode(),
                           N=16384,
                           r=8,
                           p=1,
                           buflen=190)

except ImportError:
    import pyscrypt

    def derive_key(user_password, salt):
        return pyscrypt.hash(password=user_password.encode(),
                             salt=salt.encode(),
                             N=16384,
                             r=8,
                             p=1,
                             dkLen=190)

from . import exceptions

CURRENT_VERSION = 2

HMAC_SIZE = int(256 / 8)  # 256bits in bytes
AES_BLOCK_SIZE = int(128 / 8)  # 128bits in bytes


def hmac256(key, data):
    return hmac.new(key, data, digestmod=hashlib.sha256).digest()


class AsymmetricKeyPair:
    def __init__(self, private_key, public_key):
        self.private_key = private_key
        self.public_key = public_key


class AsymmetricCryptoManager:
    def __init__(self, key_pair):
        self.key_pair = key_pair
        self._padding = asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None
        )

    @classmethod
    def generate_key_pair(cls):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=3072,
            backend=default_backend()
        )
        return AsymmetricKeyPair(
                private_key.private_bytes(encryption_algorithm=serialization.NoEncryption(),
                                          encoding=serialization.Encoding.DER,
                                          format=serialization.PrivateFormat.PKCS8),
                private_key.public_key().public_bytes(encoding=serialization.Encoding.DER,
                                                      format=serialization.PublicFormat.SubjectPublicKeyInfo))

    def decrypt(self, ctext):
        private_key = serialization.load_der_private_key(
                self.key_pair.private_key, password=None, backend=default_backend())
        return private_key.decrypt(
            ctext,
            self._padding
        )

    def encrypt(self, public_key, clear_text):
        public_key = serialization.load_der_public_key(
                self.key_pair.public_key, backend=default_backend())
        return public_key.encrypt(
            clear_text,
            self._padding
        )


class CryptoManager:
    def __init__(self, version, key, salt):
        if version > CURRENT_VERSION:
            raise exceptions.VersionTooNew("Found version is too new. Found: {} Current: {}".format(
                version, CURRENT_VERSION))
        elif version == 1:
            pass
        else:
            key = hmac256(salt, key)

        self.version = version
        self._set_derived_key(key)

    @classmethod
    def create_from_asymmetric_encryted_key(cls, version, key_pair, encrypted_key):
        asymmetric_crypto_manager = AsymmetricCryptoManager(key_pair)
        derived_key = asymmetric_crypto_manager.decrypt(encrypted_key)

        ret = CryptoManager(version, b'', b'')
        ret._set_derived_key(derived_key)
        return ret

    def _set_derived_key(self, key):
        self.cipher_key = hmac256(b'aes', key)
        self.hmacKey = hmac256(b'hmac', key)

    def decrypt(self, ctext):
        iv = ctext[:AES_BLOCK_SIZE]
        ctext = ctext[AES_BLOCK_SIZE:]
        cipher = Cipher(algorithms.AES(self.cipher_key), modes.CBC(iv), backend=default_backend())
        unpadder = padding.PKCS7(AES_BLOCK_SIZE * 8).unpadder()
        decryptor = cipher.decryptor()

        data = decryptor.update(ctext) + decryptor.finalize()
        return unpadder.update(data) + unpadder.finalize()

    def encrypt(self, clear_text):
        iv = os.urandom(AES_BLOCK_SIZE)
        cipher = Cipher(algorithms.AES(self.cipher_key), modes.CBC(iv), backend=default_backend())
        padder = padding.PKCS7(AES_BLOCK_SIZE * 8).padder()
        encryptor = cipher.encryptor()
        padded_data = padder.update(clear_text) + padder.finalize()

        return iv + encryptor.update(padded_data) + encryptor.finalize()

    def hmac(self, data):
        if self.version == 1:
            return hmac256(self.hmacKey, data)
        else:
            return hmac256(self.hmacKey, data + bytes([self.version]))
