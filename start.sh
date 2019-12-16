#! /bin/bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

openssl req -x509 -newkey rsa:4096 -nodes -days 365 \
  -out "$DIR"/cert.pem -keyout "$DIR"/key.pem \
  -subj "/C=GB/ST=London/O=CEED Ltd/emailAddress=suport@pi-top.com"

/usr/bin/python3 -B "$DIR"/pt-further-link-server.py
