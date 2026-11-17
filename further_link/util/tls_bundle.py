import asyncio
import logging
import os
import re
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import aiohttp
from cryptography import x509
from cryptography.hazmat.primitives import serialization

BUNDLE_URL = "https://storage.googleapis.com/pi-top-further-link-tls/bundle.pem"
BUNDLE_PATH = "/var/lib/further-link/tls/bundle.pem"
# Not a secret. It only stops the published key looking like a bare private key.
BUNDLE_PASSWORD = b"further-link-shared-tls"
DOMAIN = "*.further-link.pi-top.com"
VERIFY_HOSTNAME = "check.further-link.pi-top.com"
MAX_BUNDLE_BYTES = 64 * 1024

FIRST_CHECK_SECONDS = 60
CHECK_SECONDS = 12 * 60 * 60
RETRY_SECONDS = 60 * 60

_PEM_BLOCK = re.compile(rb"-----BEGIN ([A-Z ]+)-----\r?\n.+?-----END \1-----", re.S)


@dataclass
class Bundle:
    data: bytes
    # certificate chain and unencrypted key, for VNC
    pem: bytes
    not_after: datetime


def certificate_not_after(pem: bytes) -> datetime:
    cert = x509.load_pem_x509_certificate(pem)
    not_after = getattr(cert, "not_valid_after_utc", None)
    return not_after or cert.not_valid_after.replace(tzinfo=timezone.utc)


def parse_bundle(data: bytes) -> Bundle:
    blocks = [(m.group(1), m.group(0) + b"\n") for m in _PEM_BLOCK.finditer(data)]
    certs = [block for kind, block in blocks if kind == b"CERTIFICATE"]
    keys = [block for kind, block in blocks if kind == b"ENCRYPTED PRIVATE KEY"]
    if not certs or len(keys) != 1:
        raise ValueError("bundle needs certificates and one encrypted key")

    leaf = x509.load_pem_x509_certificate(certs[0])
    names = leaf.extensions.get_extension_for_class(
        x509.SubjectAlternativeName
    ).value.get_values_for_type(x509.DNSName)
    if DOMAIN not in names:
        raise ValueError(f"certificate is not for {DOMAIN}")

    key = serialization.load_pem_private_key(keys[0], password=BUNDLE_PASSWORD)
    spki = (serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    if key.public_key().public_bytes(*spki) != leaf.public_key().public_bytes(*spki):
        raise ValueError("key does not match certificate")

    plain_key = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return Bundle(
        data=data,
        pem=b"".join(certs) + plain_key,
        not_after=certificate_not_after(certs[0]),
    )


def read_saved():
    try:
        with open(BUNDLE_PATH, "rb") as f:
            return parse_bundle(f.read())
    except FileNotFoundError:
        return None
    except Exception as e:
        logging.warning(f"Ignoring saved TLS bundle: {e}")
        return None


def client_context() -> ssl.SSLContext:
    return ssl.create_default_context()


def verify_trusted(path: str) -> None:
    # A browser's view: chain to a trusted root, hostname, dates
    server_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    server_context.load_cert_chain(path, password=BUNDLE_PASSWORD)
    client_in, client_out = ssl.MemoryBIO(), ssl.MemoryBIO()
    server_in, server_out = ssl.MemoryBIO(), ssl.MemoryBIO()
    client = client_context().wrap_bio(
        client_in, client_out, server_hostname=VERIFY_HOSTNAME
    )
    server = server_context.wrap_bio(server_in, server_out, server_side=True)
    for _ in range(10):
        pending = False
        for side in (client, server):
            try:
                side.do_handshake()
            except ssl.SSLWantReadError:
                pending = True
        server_in.write(client_out.read())
        client_in.write(server_out.read())
        if not pending:
            return
    raise ValueError("TLS handshake did not complete")


def save(bundle: Bundle) -> None:
    os.makedirs(os.path.dirname(BUNDLE_PATH), exist_ok=True)
    tmp = BUNDLE_PATH + ".tmp"
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        with open(os.open(tmp, flags, 0o600), "wb") as f:
            f.write(bundle.data)
        verify_trusted(tmp)
        os.replace(tmp, BUNDLE_PATH)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def load_saved_into(context: ssl.SSLContext) -> None:
    # new connections use it; open ones keep the old certificate
    context.load_cert_chain(BUNDLE_PATH, password=BUNDLE_PASSWORD)


async def fetch() -> Bundle:
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(BUNDLE_URL) as response:
            response.raise_for_status()
            data = await response.content.read(MAX_BUNDLE_BYTES + 1)
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError("bundle too large")
    return parse_bundle(data)


async def update_once(
    context: ssl.SSLContext,
    active_not_after: datetime,
    on_update: Callable[[bytes], None],
) -> datetime:
    bundle = await fetch()
    if bundle.not_after <= active_not_after:
        return active_not_after

    save(bundle)
    load_saved_into(context)
    on_update(bundle.pem)
    logging.info(f"Using new TLS certificate, valid until {bundle.not_after}")
    return bundle.not_after


async def keep_updated(
    context: ssl.SSLContext,
    active_not_after: datetime,
    on_update: Callable[[bytes], None],
) -> None:
    delay = FIRST_CHECK_SECONDS
    while True:
        await asyncio.sleep(delay)
        try:
            active_not_after = await update_once(context, active_not_after, on_update)
            delay = CHECK_SECONDS
        except Exception as e:
            logging.warning(f"Could not update TLS certificate: {e}")
            delay = RETRY_SECONDS
