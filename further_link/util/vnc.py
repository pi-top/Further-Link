import os
from typing import Optional

from further_link.util.ssl_context import (
    SslFiles,
    cert,
    newer_saved_bundle,
    private_key,
)

VNC_CERTIFICATE_PATH = "/tmp/.further_link.vnc_ssl.pem"


def create_ssl_certificate(pem: Optional[bytes] = None) -> None:
    if pem is None:
        ssl_files = SslFiles()
        saved = newer_saved_bundle(ssl_files)
        pem = saved.pem if saved else cert(ssl_files) + private_key(ssl_files)

    tmp = VNC_CERTIFICATE_PATH + ".tmp"
    with open(tmp, "wb") as f:
        f.write(pem)
    os.replace(tmp, VNC_CERTIFICATE_PATH)
