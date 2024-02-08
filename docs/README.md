## Overview
The core of this project is a server which uses subprocess to run code and
other interactive sessions for the user and provide access to their
stdin/stdout/stderr streams.

The server can be accessed by HTTP/websocket and Bluetooth GATT protocols.
Multiple simulataneous clients are able to use it simultaneously and each can
manage multiple active processes. Multiple clients on the GATT server, which
is a broadcast system, are supported by including a client id in all messages
so that the client can distinguish which to process.

Files can be uploaded to an application-managed directory for use in the
execution. There is also a system of additional IO streams, for uses such as
video output and keyboard events, which can be used with a Python
[package](../further_link/__init__.py) provided with the server.

The server makes use of `asyncio` for concurrency, using modules such as
`asyncio.subprocess`, `aiohttp` websocket server, and `bluez-peripheral`.

## Development usage
The project requires Python 3.7+. The dependencies, command line tool and
associated python package can be installed (optionally in a virtualenv) in a
clone of the repo by running:
```
pip3 install -e ".[test]"
sudo mk-build-deps -i
```

Run the tests with:
```
pytest
```

Run the server for development with:
```
FURTHER_LINK_NOSSL=1 python3 further_link/__main__.py
```

Confirm the server is running with:
```
curl http://localhost:8028/status
```

## Configuration
### Port
The default server port, __8028__, can be overridden by setting
FURTHER_LINK_PORT env variable.

### SSL/TLS
The server uses TLS by default but the required certificates are not
provided in this repository. For development and testing you can disable TLS
by setting environment variable FURTHER_LINK_NOSSL=1. Alternatively, you can
provide your own certificate and key files by placing them in the `extra`
directory with the names `cert.pem` and `key.pem`.

### Working directory
The default working directory where files are uploaded and executed from is
`~/further`. This can be overridden by setting env var FURTHER_LINK_WORK_DIR.

### Client
A client reference is not currently provided in this repo. The primary client
is built into the Further frontend although these docs and the project e2e
tests provide some insight into how it works.

## API
### Bluetooth
The Bluetooth API is not currently documented here but is based on the
HTTP/websocket API. The primary differences are that a `client` property is
required in all messages to identify the client source/destination, and that
messages are broken into chunks by an additional protocol to support the low
max message length of GATT.

### HTTP Post /upload
- Body should be a JSON object with `name` of directory to upload into and
  `files` object. Files are provided as `text` type, with the text content, or
  `url` type, with a url for the file to be downloaded from
  ([example](../tests/test_data/upload_data.py)). If the server does not have
  internet access then url type files will be ignored. Reponse is a json
  which includes whether the url type files were downloaded:
  `{ "success": true, "fetched_urls": true }`.

### Websocket Endpoint /run
Each websocket client connected on `/run` can manage multuiple processes of
different types, addressing them by a unique id.

#### Example usage
- Connect websocket on `/run` (using [websocat](https://github.com/vi/websocat)):
```
websocat ws://localhost:8028/run
```

- Send `start` command for process id 1, requesting `runner` "python3" and `code`:
```
{ "type": "start", "process": "1", "data": { "runner": "python3", "code": "print('hi')" } }
```

- Receive `started` response with expected id:
```
{ "type": "started", "process": "1" }
```

- Send `start` command for process id 2 requesting `runner` "shell":
```
{ "type": "start", "process": "2", "data": { "runner": "shell" } }
```

- Receive `started` response with expected id:
```
{ "type": "started", "process": "2" }
```

- Send `stdin` to shell process with id 2:
```
{ "type": "stdin", "process": "2", "data": { "input": "ls\n" } }
```

- Receive `stdout` response from python:
```
{ "type": "stdout", "process": "1", "data": { "output": "hi\n" } }
```

- Receive `stdout` response from shell:
```
{ "type": "stdout", "process": "2", "data": { "output": ".\n..\nfile.txt\n" } }
```

- Receive `stopped` response from python:
```
{ "type": "stopped", "process": "1", "data": { "exitCode": 0 } }
```

#### Spec
##### Options
This connection has some options which can be selected with query
parameters:

```
/run?user=root
```
The `user` parameter is used to select the Linux user which the code is
executed as. By default the `pi` user is selected if it exists, otherwise
the user executing the server is used.

```
/run?pty=1
```
The pty parameter, if set to 1 or true, will create a pseudoterminal interface
for the python process IO streams, in order to provide terminal behaviours such
as 'cooked mode'. This is useful to produce identical behaviour of programs to
that on the command line and to easily interface with terminal emulators such
as [xterm.js](https://github.com/xtermjs/xterm.js/).

##### Message Types
Websocket messages sent between client and server are in JSON with three top
level properties: required string `type`, optional string `process` and optional object `data`.

Message types accepted by the server are:
```
{
 "type":"[ping|start|stop|stdin|resize|keyevent]",
 "data": {...},
 "process": "id"
}
```

Message types sent from the server are:
```
{
 "type":"[pong|error|started|stopped|stdout|stderr|novncOptions|video|keylisten]",
 "data": {...},
 "process": "id"
}
```

Message and response details:
Connection management - these messages don't require a process id
- `ping` command from the client will be met with a `pong` response from
    the server. This can be used to keep the socket active to prevent automatic
    closures.
- `pong` response is sent by the server immediately after a `ping` is received
<br>

- `error` response is sent for bad commands or server errors e.g. `data: { message: "something went wrong and it's not your python code" }`
<br>

Basic:
// TODO non python!
- `start` command will start a new python process. This can run an existing
    python file or create one from the `code` data field. The `path` data field
    is used to specify the path of a python file to run, or the directory in
    which to create the file from `code`. The working directory for the python
    process is the directory the entrypoint file is in, or /tmp. If `path` is
    not absolute, it is assumed to be relative to the further link working
    directory described above.

    A 'novncOptions' object can also be passed in the start data to configure a
    virtual display for the process, attach a vnc server to it and serve it via
    the novnc websocket proxy, for viewing from a browser. When a window is
    detected on the virtual display, a 'novnc' response will be sent to inform
    the browser of the activity and provide a url to view it. 'novncOptions'
    can include a boolean property 'enabled' and 'width' and 'height' integers
    for the display dimensions.

    e.g.
    `data: {code:"print('hi')"}`
    `data: {code:"print('hi')", path: "myproject"}`
    `data: {path: "myproject/run.py", novncOptions: {enabled: true}}`
    `data: {path: "/home/pi/run.py"}`

- `started` response is sent after a successful process `start`, has no data.
<br>

- `stdin` command is used to send data to process stdin e.g. `data: { input: "this can be read by python\n" }`.
- `stdout` response is sent when process prints to stdout. e.g. `data: { output: "this was printed by python" }`
- `stderr` response is sent when process prints to stderr e.g. `data: { output: "Traceback bleh bleh" }`
<br>

- `stop` command is used to stop a running process early, has no data.
- `stopped` response is sent when a process finished and has the exit code in e.g. `data: { exitCode: 0 }`
<br>

Advanced
- `novnc` response is sent by the server with data.port containing a port
    number and data.path containing a url path. These can be used to construct
    the url of a vnc client to view graphical output of the process.
<br>

- `video` response is sent by the server with data.output containing a base64
    encoded mjpeg frame for the client to render as a video feed.
<br>

- `keylisten` message is sent by the server to indicate it would like to
    receive keyboard events from the client for a specific key. This would be
    initiated by user code using the further_link.KeyboardButton python module.
    Keys are specified as web [KeyboardEvent.key](https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key)
    strings e.g. `data: { key: "ArrowUp" }`
- `keyevent` message is sent by the client to provide keyboard events to the
    server so that they can be forwarded to user code using
    further_link.KeyboardButton. The data includes a key string matching those
    used in `keylisten` and an event string which is either "keydown" or
    "keyup" e.g. `data: { key: "ArrowUp", event: "keydown" }`
<br>

There is no upload message for this api. The separate http endpoint should be
used instead.

## Notes
### Projects that make interesting comparison:
- https://github.com/LLK/scratch-link
- https://github.com/billchurch/webssh2
- https://github.com/huashengdun/webssh
- https://github.com/replit/polygott

### Ideas
- Other languages & environments (SonicPi, .NET interactive...)
- Connection security via login or codes displayed on OLED
- Detaching, reattaching to long running programs
- Device status endpoints eg battery
- Queueing system to enable safe hardware sharing
- Device registration to remote server to provide easier connection
- More IO extensions eg chart plotting, ui events
