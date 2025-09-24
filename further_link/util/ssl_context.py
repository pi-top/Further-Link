import codecs
import datetime
import ipaddress
import logging
import os
import ssl
from typing import Dict, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from OpenSSL.crypto import FILETYPE_PEM, dump_privatekey, load_privatekey

tls_exception = Exception(
    """
    TLS configuration error!
    Set the environment variable FURTHER_LINK_NOSSL=1 to run the server without
    TLS or consult the TLS section of the project readme for more information.\
"""
)


class SslFiles:
    def __init__(self) -> None:
        file_dir = os.path.dirname(os.path.realpath(__file__))
        cert_dir = os.path.join(file_dir, "../extra")

        self.cert = os.path.join(cert_dir, "cert.pem")
        self.own_key = os.path.join(cert_dir, "key.pem")
        self.encrypted_key = os.path.join(cert_dir, "key.aes.pem")
        self.data_file = os.path.join(cert_dir, "fl.dat")


# Cache for generated certificates
CERT_CACHE: Dict[str, Tuple[bytes, bytes]] = {}


def generate_self_signed_cert(hostname: str) -> Tuple[bytes, bytes]:
    """Generate a self-signed SSL certificate for a given hostname or IP."""
    print(hostname)
    if hostname in CERT_CACHE:
        return CERT_CACHE[hostname]

    logging.info(f"Generating self-signed certificate for {hostname}")

    # Generate a new private key
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Create subject and issuer
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
        ]
    )

    print(subject)

    # Determine if hostname is an IP address
    try:
        ip = ipaddress.ip_address(hostname)
        san = [x509.IPAddress(ip)]
    except ValueError:
        # It's a hostname, not an IP
        san = [x509.DNSName(hostname)]
    print(san)

    # Create the certificate
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(san),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    # Convert to PEM format
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Cache the certificate and key
    CERT_CACHE[hostname] = (cert_pem, key_pem)
    return cert_pem, key_pem


def sni_callback(sock, sni_name, _):
    """Callback for SSL SNI (Server Name Indication).
    This is called during the SSL/TLS handshake when the client sends SNI.
    The sni_callback should NOT return a context - it should modify the socket or
    set certificates directly.
    """
    print(f"Received SNI: {sni_name}")
    try:
        # Get client IP if no SNI is provided
        if not sni_name:
            print("No SNI provided, getting client IP address")
            try:
                # Get client address directly from the socket
                if hasattr(sock, "getpeername"):
                    client_addr, _ = sock.getpeername()
                    print(f"Using client IP address: {client_addr}")
                    sni_name = client_addr
                else:
                    # If we can't get the client address, use a default IP
                    print("Unable to get client IP, using 127.0.0.1")
                    sni_name = "127.0.0.1"
            except Exception as e:
                print(f"Error getting client address: {e}")
                # Default to localhost
                sni_name = "127.0.0.1"

        # Check if this is an IP address connection
        try:
            ipaddress.ip_address(sni_name)
            is_ip = True
        except ValueError:
            is_ip = False

        # If it's not an IP address and we're not forcing cert generation, use default cert
        if not is_ip and not os.environ.get(
            "FURTHER_LINK_ALWAYS_GENERATE_CERT", "0"
        ).lower() in ["1", "true"]:
            return None

        logging.info(f"Using dynamic certificate for connection to {sni_name}")

        # Generate a dynamic certificate for this SNI name
        cert_pem, key_pem = generate_self_signed_cert(sni_name)

        # Create temporary files for the certificate and key
        cert_file = ssl_ctx_data_to_file(cert_pem)
        key_file = ssl_ctx_data_to_file(key_pem)

        # Update the context directly with our new certificate
        # We get the context from the socket
        context = sock.context
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)

        return None
    except Exception as e:
        logging.error(f"Error in SNI callback: {e}")
        return None


def ssl_ctx_data_to_file(data: bytes) -> str:
    """Helper to convert binary cert data to a file path for ssl.load_cert_chain."""
    import atexit
    import tempfile

    # Create a temp file
    fd, path = tempfile.mkstemp()

    # Make sure to clean up temp files on exit
    atexit.register(lambda p: os.path.exists(p) and os.unlink(p), path)

    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return path
    except Exception:
        os.unlink(path)
        raise


def ssl_context() -> Optional[ssl.SSLContext]:
    # use ssl if FURTHER_LINK_NOSSL is unset, 0 or false
    if os.environ.get("FURTHER_LINK_NOSSL", "0").lower() not in ["0", "false"]:
        return None

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_files = SslFiles()

    try:
        if os.path.isfile(ssl_files.own_key):
            context.load_cert_chain(certfile=ssl_files.cert, keyfile=ssl_files.own_key)
        else:
            context.load_cert_chain(
                certfile=ssl_files.cert,
                keyfile=ssl_files.encrypted_key,
                password=lambda: password(ssl_files),
            )
    except (FileNotFoundError, ssl.SSLError):
        raise tls_exception from None

    # Set SNI callback for dynamic certificate generation
    context.sni_callback = sni_callback

    return context


def password(ssl_files: SslFiles) -> str:
    with open(ssl_files.data_file) as file:
        return codecs.getencoder("rot-13")(file.read()[:-1])[0]


def private_key(ssl_files: SslFiles) -> bytes:
    with open(ssl_files.encrypted_key, "rb") as f:
        buffer = f.read()

    key = load_privatekey(
        type=FILETYPE_PEM, buffer=buffer, passphrase=f"{password(ssl_files)}".encode()
    )

    return dump_privatekey(
        type=FILETYPE_PEM, pkey=key, passphrase=f"{password(ssl_files)}".encode()
    )


def cert(ssl_files: SslFiles) -> bytes:
    with open(ssl_files.cert, "rb") as f:
        cert = f.read()
    return cert
