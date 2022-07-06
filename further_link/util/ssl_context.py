import codecs
import os
import ssl

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


def ssl_context():
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

    return context


def password(ssl_files: SslFiles):
    with open(ssl_files.data_file) as file:
        return codecs.getencoder("rot-13")(file.read()[:-1])[0]


def private_key(ssl_files: SslFiles):
    with open(ssl_files.encrypted_key, "rb") as f:
        buffer = f.read()

    key = load_privatekey(
        type=FILETYPE_PEM, buffer=buffer, passphrase=f"{password(ssl_files)}".encode()
    )

    return dump_privatekey(
        type=FILETYPE_PEM, pkey=key, passphrase=f"{password(ssl_files)}".encode()
    )


def cert(ssl_files: SslFiles):
    with open(ssl_files.cert, "rb") as f:
        cert = f.read()
    return cert
