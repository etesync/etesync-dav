import os
import sys
from subprocess import check_call

from etesync_dav.config import SSL_KEY_FILE, SSL_CERT_FILE

KEY_CIPHER = 'rsa'
KEY_SIZE = 4096
KEY_DAYS = 3650  # That's 10 years.


class Error(Exception):
    pass


def has_ssl():
    return os.path.exists(SSL_KEY_FILE) and os.path.exists(SSL_CERT_FILE)


def needs_ssl():
    return sys.platform == 'darwin' and not has_ssl()


def generate_cert(cert_path: str = SSL_CERT_FILE, key_path: str = SSL_KEY_FILE,
                  key_cipher: str = KEY_CIPHER, key_size: int = KEY_SIZE,
                  key_days: int = KEY_DAYS):
    if os.path.exists(key_path):
        print('Skipping key generation as already exists.')
        return

    check_call(['openssl', 'req', '-x509', '-nodes',
                '-newkey', key_cipher + ':' + str(key_size),
                '-keyout', key_path, '-out', cert_path, '-days', str(key_days),
                '-subj', '/CN=localhost'])


def macos_trust_cert(cert_path: str = SSL_CERT_FILE, keychain: str = ''):
    if sys.platform != 'darwin':
        raise Error('this is not macOS.')
    keychain_option = ['-k', keychain] if keychain else []
    check_call(['security', 'import', cert_path] + keychain_option)
    check_call(['security', 'add-trusted-cert', '-p', 'ssl', cert_path] + keychain_option)
