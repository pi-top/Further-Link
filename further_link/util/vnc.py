from pathlib import Path

from further_link.util.ssl_context import SslFiles, cert, private_key

VNC_CERTIFICATE_PATH = "/tmp/.further_link.vnc_ssl.pem"


def create_ssl_certificate() -> None:
    vnc_cert = Path(VNC_CERTIFICATE_PATH)
    if vnc_cert.exists():
        return
    vnc_cert.touch(exist_ok=True)

    ssl_files = SslFiles()
    with open(VNC_CERTIFICATE_PATH, "w") as f:
        for data in (cert(ssl_files), private_key(ssl_files)):
            f.write(data.decode("utf-8"))
