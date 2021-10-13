.. image:: https://img.shields.io/github/v/tag/pi-top/Further-Link
    :target: https://github.com/pi-top/Further-Link/tags
    :alt: GitHub tag (latest by date)

.. image:: https://img.shields.io/github/v/release/pi-top/Further-Link
    :target: https://github.com/pi-top/Further-Link/releases
    :alt: GitHub release (latest by date)

.. image:: https://img.shields.io/github/workflow/status/pi-top/Further-Link/Run%20Tests%20and%20Upload%20Coverage%20Report
    :target: https://github.com/pi-top/Further-Link/actions?query=workflow%3A%22Run+Tests+and+Upload+Coverage+Report%22+branch%3Amaster
    :alt: GitHub Workflow Status

.. image:: https://img.shields.io/codecov/c/gh/pi-top/Further-Link?token=hfbgB9Got4
    :target: https://app.codecov.io/gh/pi-top/Further-Link
    :alt: Codecov

============
Further Link
============

Further Link is a web server application, intended to run on `pi-top`_
hardware, which allows communicating with the device from `pi-top Further`_.

The primary use case of this is to remotely run Further user's code (python3
usually) on the pi-top, with full interactivity via a websocket api.

Additional features include uploading files; interactive shell sessions;
additional IO capabilities, such as video output and keyboard event input,
though an inbuilt python library (see `examples <examples>`_).

`further-link` is included out-of-the-box with pi-topOS.

Ensure that you keep your system up-to-date to enjoy the latest features and
bug fixes.

This application is installed as a Python 3 script that is managed by a systemd
service, configured to automatically run on startup and restart during software
updates.

.. _pi-top: https://www.pi-top.com
.. _pi-top Further: https://further.pi-top.com

------------
Installation
------------

`further-link` is installed out of the box with pi-topOS, which is available
from pi-top.com_. To install on Raspberry Pi OS or other operating systems,
check out the `Using pi-top Hardware with Raspberry Pi OS`_ page on the pi-top
knowledge base.

.. _pi-top.com: https://www.pi-top.com/products/os/
.. _Using pi-top Hardware with Raspberry Pi OS: https://pi-top.com/pi-top-rpi-os

----------------
More Information
----------------

Please refer to the `additional documentation`_ for more
information about the application.

.. _additional documentation: docs/README.md
