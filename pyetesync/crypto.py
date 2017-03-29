import pyaes
import hashlib
import hmac

CURRENT_VERSION = 2

HMAC_SIZE = int(256 / 8)  # 256bits in bytes
AES_BLOCK_SIZE = int(128 / 8)  # 128bits in bytes


def hmac256(key, data):
    return hmac.new(key, data, digestmod=hashlib.sha256).digest()


class CryptoManager:
    def __init__(self, version, key, salt):
        if version > CURRENT_VERSION:
            raise Exception("Version is out of range")
        elif version == 1:
            pass
        else:
            key = hmac256(salt, key)

        self.version = version
        self.cipherKey = hmac256(b'aes', key)
        self.hmacKey = hmac256(b'hmac', key)

    def decrypt(self, ctext):
        iv = ctext[:AES_BLOCK_SIZE]
        ctext = ctext[AES_BLOCK_SIZE:]
        aes = pyaes.Decrypter(pyaes.AESModeOfOperationCBC(self.cipherKey, iv=iv))

        ret = aes.feed(ctext)
        ret += aes.feed()
        return ret

    def hmac(self, data):
        if self.version == 1:
            return hmac256(self.hmacKey, data)
        else:
            return hmac256(self.hmacKey, data + bytes([self.version]))
