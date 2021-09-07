============
Further Link
============

--------------------
Build Status: Latest
--------------------

.. image:: https://img.shields.io/github/workflow/status/pi-top/Further-Link/Test%20and%20Build%20Packages%20on%20All%20Commits
   :alt: GitHub Workflow Status

.. image:: https://img.shields.io/github/v/tag/pi-top/Further-Link
    :alt: GitHub tag (latest by date)

.. image:: https://img.shields.io/github/v/release/pi-top/Further-Link
    :alt: GitHub release (latest by date)

.. https://img.shields.io/codecov/c/gh/pi-top/Further-Link?token=hfbgB9Got4
..   :alt: Codecov

-----
About
-----

Further Link is a web server application, intended to run on
[pi-top](https://www.pi-top.com) hardware, which allows communicating with the
device from [pi-top Further](https://further.pi-top.com). The
primary use case of this is to remotely run Further user's code (`python3`) on
the pi-top.

A websocket API is provided via `aiohttp` and `asyncio` subprocesses to start and stop Python programs and access their stdin/stdout/stderr streams. File can be uploaded to a directory for use in the execution. There is also a system of additional IO streams, for
uses such as video output and keyboard events, which can be used with special
Python module accessible to run by the server. Check out the examples folder.

`further-link` is included out-of-the-box with pi-topOS.

Ensure that you keep your system up-to-date to enjoy the latest features and bug fixes.

This application is installed as a Python 3 script that is managed by a systemd service, configured to automatically run on startup and restart during software updates.

------------
Installation
------------

`further-link` is installed out of the box with pi-topOS, which is available from
pi-top.com_. To install on Raspberry Pi OS or other operating systems, check out the `Using pi-top Hardware with Raspberry Pi OS`_ page on the pi-top knowledge base.

.. _pi-top.com: https://www.pi-top.com/products/os/

.. _Using pi-top Hardware with Raspberry Pi OS: https://knowledgebase.pi-top.com/knowledge/pi-top-and-raspberry-pi-os

----------------
More Information
----------------

Please refer to the `additional documentation`_ for more
information about the application.

.. _More Info: https://github.com/pi-top/Further-Link/blob/master/docs/README.md
