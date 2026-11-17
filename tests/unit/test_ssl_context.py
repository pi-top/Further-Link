import codecs
import ssl
from datetime import timedelta
from types import SimpleNamespace

import pytest
from cryptography import x509

from further_link.util import ssl_context as ssl_context_module
from further_link.util import tls_bundle, vnc

from .tls_helpers import (  # noqa: F401
    NOW,
    encrypted,
    handshake_certificate,
    make_cert,
    make_key,
    trust_test_ca,
)

PACKAGED_DAYS = 30


@pytest.fixture
def packaged(tmp_path, monkeypatch):
    key = make_key()
    cert = make_cert(key, days=PACKAGED_DAYS)
    files = SimpleNamespace(
        cert=str(tmp_path / "cert.pem"),
        own_key=str(tmp_path / "key.pem"),
        encrypted_key=str(tmp_path / "key.aes.pem"),
        data_file=str(tmp_path / "fl.dat"),
    )
    (tmp_path / "cert.pem").write_bytes(cert)
    (tmp_path / "key.aes.pem").write_bytes(encrypted(key, b"packaged"))
    (tmp_path / "fl.dat").write_text(codecs.encode("packaged", "rot13") + "\n")

    monkeypatch.setattr(ssl_context_module, "SslFiles", lambda: files)
    monkeypatch.setattr(vnc, "SslFiles", lambda: files)
    monkeypatch.setattr(vnc, "VNC_CERTIFICATE_PATH", str(tmp_path / "vnc.pem"))
    monkeypatch.setattr(tls_bundle, "BUNDLE_PATH", str(tmp_path / "tls/bundle.pem"))
    monkeypatch.delenv("FURTHER_LINK_NOSSL", raising=False)
    return x509.load_pem_x509_certificate(cert)


def save_bundle(days):
    key = make_key()
    cert = make_cert(key, days=days)
    tls_bundle.save(tls_bundle.parse_bundle(cert + encrypted(key)))
    return x509.load_pem_x509_certificate(cert)


def vnc_certificate():
    vnc.create_ssl_certificate()
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(vnc.VNC_CERTIFICATE_PATH)
    return handshake_certificate(context)


def test_packaged_certificate_without_saved_bundle(packaged):
    assert handshake_certificate(ssl_context_module.ssl_context()) == packaged
    assert ssl_context_module.active_not_after() == NOW + timedelta(days=PACKAGED_DAYS)
    assert vnc_certificate() == packaged


def test_newer_saved_bundle_wins(packaged):
    saved = save_bundle(days=90)

    assert handshake_certificate(ssl_context_module.ssl_context()) == saved
    assert ssl_context_module.active_not_after() == NOW + timedelta(days=90)
    assert vnc_certificate() == saved


def test_older_saved_bundle_ignored(packaged):
    save_bundle(days=10)

    assert handshake_certificate(ssl_context_module.ssl_context()) == packaged
    assert ssl_context_module.active_not_after() == NOW + timedelta(days=PACKAGED_DAYS)
    assert vnc_certificate() == packaged


def test_vnc_certificate_rewritten_with_given_pem(packaged):
    vnc.create_ssl_certificate()
    key = make_key()
    bundle = tls_bundle.parse_bundle(make_cert(key) + encrypted(key))

    vnc.create_ssl_certificate(bundle.pem)

    with open(vnc.VNC_CERTIFICATE_PATH, "rb") as f:
        assert f.read() == bundle.pem
