import codecs
import os
import ssl

tls_exception = Exception(
    """
    TLS configuration error!
    Set the environment variable FURTHER_LINK_NOSSL=1 to run the server without
    TLS or consult the TLS section of the project readme for more information.\
"""
)


def ssl_context():
    # use ssl if FURTHER_LINK_NOSSL is unset, 0 or false
    if os.environ.get("FURTHER_LINK_NOSSL", "0").lower() not in ["0", "false"]:
        return None

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

    file_dir = os.path.dirname(os.path.realpath(__file__))
    cert_dir = os.path.join(file_dir, "../../extra")
    cert = os.path.join(cert_dir, "cert.pem")
    own_key = os.path.join(cert_dir, "key.pem")
    encrypted_key = os.path.join(cert_dir, "key.aes.pem")
    data_file = os.path.join(cert_dir, "fl.dat")

    try:
        if os.path.isfile(own_key):
            context.load_cert_chain(certfile=cert, keyfile=own_key)
        else:

            def password():
                with open(data_file) as file:
                    return codecs.getencoder("rot-13")(file.read()[:-1])[0]

            context.load_cert_chain(
                certfile=cert, keyfile=encrypted_key, password=password
            )
    except (FileNotFoundError, ssl.SSLError):
        raise tls_exception from None

    return context
