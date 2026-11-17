import ssl
from datetime import timedelta

import pytest
from aioresponses import aioresponses as mock_http
from cryptography import x509

from further_link.util import tls_bundle

from .tls_helpers import (  # noqa: F401
    NOW,
    encrypted,
    handshake_certificate,
    make_bundle,
    make_cert,
    make_key,
    trust_test_ca,
)


@pytest.fixture
def http():
    with mock_http() as m:
        yield m


@pytest.fixture
def bundle_path(tmp_path, monkeypatch):
    path = tmp_path / "tls" / "bundle.pem"
    monkeypatch.setattr(tls_bundle, "BUNDLE_PATH", str(path))
    return path


def test_parse_bundle():
    data = make_bundle(days=90)
    bundle = tls_bundle.parse_bundle(data)

    assert bundle.data == data
    assert bundle.not_after == NOW + timedelta(days=90)
    assert b"BEGIN CERTIFICATE" in bundle.pem
    assert b"BEGIN PRIVATE KEY" in bundle.pem
    assert b"ENCRYPTED" not in bundle.pem


def test_parse_bundle_keeps_chain_order():
    key = make_key()
    leaf = make_cert(key)
    intermediate = make_cert(make_key(), names=("Intermediate",))
    bundle = tls_bundle.parse_bundle(leaf + intermediate + encrypted(key))

    assert bundle.pem.startswith(leaf + intermediate)


@pytest.mark.parametrize(
    "data",
    [
        make_bundle(names=("example.com",)),
        make_cert(make_key()) + encrypted(make_key()),
        make_cert(make_key()),
        b"<html>not found</html>",
    ],
    ids=["wrong domain", "key mismatch", "no key", "not pem"],
)
def test_parse_bundle_rejects(data):
    with pytest.raises(ValueError):
        tls_bundle.parse_bundle(data)


def test_parse_bundle_rejects_wrong_password():
    key = make_key()
    with pytest.raises((ValueError, TypeError)):
        tls_bundle.parse_bundle(make_cert(key) + encrypted(key, b"other"))


def test_save_and_load(bundle_path):
    bundle = tls_bundle.parse_bundle(make_bundle())
    tls_bundle.save(bundle)

    assert bundle_path.read_bytes() == bundle.data
    assert bundle_path.stat().st_mode & 0o777 == 0o600
    assert tls_bundle.read_saved().not_after == bundle.not_after
    tls_bundle.load_saved_into(ssl.create_default_context(ssl.Purpose.CLIENT_AUTH))


def test_save_rejects_untrusted_certificate(bundle_path):
    bundle = tls_bundle.parse_bundle(make_bundle(self_signed=True))

    with pytest.raises(ssl.SSLCertVerificationError):
        tls_bundle.save(bundle)
    assert not bundle_path.exists()
    assert list(bundle_path.parent.iterdir()) == []


def test_save_rejects_expired_certificate(bundle_path):
    bundle = tls_bundle.parse_bundle(make_bundle(days=-1))

    with pytest.raises(ssl.SSLCertVerificationError):
        tls_bundle.save(bundle)
    assert not bundle_path.exists()


def test_read_saved_missing_or_bad(bundle_path):
    assert tls_bundle.read_saved() is None

    bundle_path.parent.mkdir()
    bundle_path.write_bytes(b"garbage")
    assert tls_bundle.read_saved() is None


@pytest.mark.asyncio
async def test_update_once_uses_newer_bundle(http, bundle_path, mocker):
    data = make_bundle(days=90)
    http.get(tls_bundle.BUNDLE_URL, body=data)
    context = mocker.Mock()
    on_update = mocker.Mock()

    not_after = await tls_bundle.update_once(context, NOW, on_update)

    assert not_after == NOW + timedelta(days=90)
    assert bundle_path.read_bytes() == data
    context.load_cert_chain.assert_called_once_with(
        str(bundle_path), password=tls_bundle.BUNDLE_PASSWORD
    )
    on_update.assert_called_once_with(tls_bundle.parse_bundle(data).pem)


@pytest.mark.asyncio
async def test_update_once_ignores_older_bundle(http, bundle_path, mocker):
    http.get(tls_bundle.BUNDLE_URL, body=make_bundle(days=30))
    context = mocker.Mock()
    on_update = mocker.Mock()
    active = NOW + timedelta(days=60)

    assert await tls_bundle.update_once(context, active, on_update) == active
    assert not bundle_path.exists()
    context.load_cert_chain.assert_not_called()
    on_update.assert_not_called()


@pytest.mark.asyncio
async def test_update_once_rejects_untrusted_bundle(http, bundle_path, mocker):
    http.get(tls_bundle.BUNDLE_URL, body=make_bundle(self_signed=True))
    context = mocker.Mock()
    on_update = mocker.Mock()

    with pytest.raises(ssl.SSLCertVerificationError):
        await tls_bundle.update_once(context, NOW, on_update)
    context.load_cert_chain.assert_not_called()
    on_update.assert_not_called()


@pytest.mark.asyncio
async def test_update_once_http_error(http, bundle_path, mocker):
    http.get(tls_bundle.BUNDLE_URL, status=404)
    with pytest.raises(Exception):
        await tls_bundle.update_once(mocker.Mock(), NOW, mocker.Mock())
    assert not bundle_path.exists()


@pytest.mark.asyncio
async def test_update_once_rejects_large_bundle(http, bundle_path, mocker):
    http.get(tls_bundle.BUNDLE_URL, body=b"x" * (tls_bundle.MAX_BUNDLE_BYTES + 1))
    with pytest.raises(ValueError):
        await tls_bundle.update_once(mocker.Mock(), NOW, mocker.Mock())


def test_new_certificate_served_without_restart(bundle_path, tmp_path):
    old_key, new_key = make_key(), make_key()
    old_cert = make_cert(old_key, days=10)
    (tmp_path / "old.pem").write_bytes(old_cert + encrypted(old_key))
    server = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    server.load_cert_chain(
        str(tmp_path / "old.pem"), password=tls_bundle.BUNDLE_PASSWORD
    )

    new_cert = make_cert(new_key, days=90)
    tls_bundle.save(tls_bundle.parse_bundle(new_cert + encrypted(new_key)))
    tls_bundle.load_saved_into(server)

    assert handshake_certificate(server) == x509.load_pem_x509_certificate(new_cert)
