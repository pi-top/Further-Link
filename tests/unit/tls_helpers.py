import ssl
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from further_link.util import tls_bundle

NOW = datetime.now(timezone.utc).replace(microsecond=0)


def make_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_ca():
    key = make_key()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test CA")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(NOW - timedelta(days=1))
        .not_valid_after(NOW + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False
        )
        .sign(key, hashes.SHA256())
    )
    return key, cert


CA_KEY, CA_CERT = make_ca()


def make_cert(key, days=90, names=("*.further-link.pi-top.com",), self_signed=False):
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, names[0])])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name if self_signed else CA_CERT.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(NOW - timedelta(days=1))
        .not_valid_after(NOW + timedelta(days=days))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(n) for n in names]),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(
                (key if self_signed else CA_KEY).public_key()
            ),
            critical=False,
        )
        .sign(key if self_signed else CA_KEY, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM)


@pytest.fixture(autouse=True)
def trust_test_ca(monkeypatch):
    def client_context():
        context = ssl.create_default_context(
            cadata=CA_CERT.public_bytes(serialization.Encoding.PEM).decode()
        )
        return context

    monkeypatch.setattr(tls_bundle, "client_context", client_context)


def encrypted(key, password=tls_bundle.BUNDLE_PASSWORD):
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(password),
    )


def make_bundle(days=90, names=("*.further-link.pi-top.com",), self_signed=False):
    key = make_key()
    return make_cert(key, days, names, self_signed) + encrypted(key)


def handshake_certificate(server_context):
    client_context = ssl.create_default_context()
    client_context.check_hostname = False
    client_context.verify_mode = ssl.CERT_NONE
    client_in, client_out = ssl.MemoryBIO(), ssl.MemoryBIO()
    server_in, server_out = ssl.MemoryBIO(), ssl.MemoryBIO()
    client = client_context.wrap_bio(client_in, client_out)
    server = server_context.wrap_bio(server_in, server_out, server_side=True)
    for _ in range(10):
        for side in (client, server):
            try:
                side.do_handshake()
            except ssl.SSLWantReadError:
                pass
        server_in.write(client_out.read())
        client_in.write(server_out.read())
    return x509.load_der_x509_certificate(client.getpeercert(binary_form=True))
