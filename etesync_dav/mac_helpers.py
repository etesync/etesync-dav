# Copyright © 2017 Tom Hacohen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import sys
from datetime import datetime, timedelta
from subprocess import check_call

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from etesync_dav.config import SSL_KEY_FILE, SSL_CERT_FILE

KEY_CIPHER = 'rsa'
KEY_SIZE = 4096
KEY_DAYS = 3650  # That's 10 years.

ON_MAC = sys.platform == 'darwin'
ON_WINDOWS = sys.platform in ['win32', 'cygwin']


class Error(Exception):
    pass


def has_ssl():
    return os.path.exists(SSL_KEY_FILE) and os.path.exists(SSL_CERT_FILE)


def needs_ssl():
    return (ON_MAC or ON_WINDOWS) and \
        not has_ssl()

def generate_cert(cert_path: str = SSL_CERT_FILE, key_path: str = SSL_KEY_FILE,
                  key_size: int = KEY_SIZE, key_days: int = KEY_DAYS):
    if os.path.exists(key_path):
        print('Skipping key generation as already exists.')
        return

    hostname = 'localhost'

    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend(),
    )

    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, hostname)
    ])

    # best practice seem to be to include the hostname in the SAN, which *SHOULD* mean COMMON_NAME is ignored.
    alt_names = [x509.DNSName(hostname)]

    san = x509.SubjectAlternativeName(alt_names)

    # prevent this cert form being used to sign other certs
    basic_contraints = x509.BasicConstraints(ca=False, path_length=None)
    now = datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1000)
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=key_days))
        .add_extension(basic_contraints, False)
        .add_extension(san, False)
        .sign(key, hashes.SHA256(), default_backend())
    )
    cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    with open(key_path, 'wb') as f:
        f.write(key_pem)
    with open(cert_path, 'wb') as f:
        f.write(cert_pem)


def macos_trust_cert(cert_path: str = SSL_CERT_FILE):
    if not ON_MAC:
        raise Error('this is not macOS.')
    check_call(['security', 'import', cert_path])
    check_call(['security', 'add-trusted-cert', '-p', 'ssl', cert_path])


def windows_trust_cert(cert_path: str = SSL_CERT_FILE):
    if not ON_WINDOWS:
        raise Error('this is not Windows.')
    check_call(['powershell.exe', 'Import-Certificate', '-FilePath', '"{}"'.format(cert_path), '-CertStoreLocation', 'Cert:\CurrentUser\Root'])


def trust_cert(cert_path: str = SSL_CERT_FILE):
    if ON_WINDOWS:
        windows_trust_cert(cert_path)
    elif ON_MAC:
        macos_trust_cert(cert_path)
    else:
        raise Error('Only supported on windows/macOS')
