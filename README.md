# pt-further-link
This project is intended to run on a pi-top[4], to allow connecting to the
revice from [Further](https://further.pi-top.com).

The primary use case of this is to remotely run user's code (python3) on the
pi-top. A websocket api is provided to start and stop python programs and
access their stdin/out/err streams.

### Usage
We are using Python 3.7 and managing dependencies with
[pipenv](https://github.com/pypa/pipenv)
```
pipenv shell
pipenv sync
python3 server.py
```

The default server port, __8028__, can be changed by setting FURTHER_LINK_PORT env variable.
The default working directory where temporary files are created, /tmp , can be changed by setting FURTHER_LINK_WORK_DIR env variable.

To allow connecting to a local server with valid ssl, this server uses a ssl
cert for *.further-link.pi-top.com, and we create dns records to point that
hostname to local ip addresses. So if you are running this on localhost:
```
curl https://127-0-0-1.further-link.pi-top.com:8028/status
```

### Websocket API
#### Example usage
- Connect websocket on `/exec` (using [websocat](https://github.com/vi/websocat)):
```
websocat wss://127-0-0-1.further-link.pi-top.com:8028/exec
```
- Send `start` command with `sourceScript`:
```
{ "type": "start", "data": { "sourceScript": "print('hi')" } }
```
- Recieve `stdout` response:
```
{ "type": "stdout", "data": { "output": "hi\n" } }
```
- Recieve `stopped` response:
```
{ "type": "stopped", "data": { "exitCode": 0 } }
```

#### Spec
Each websocket client connected on `/exec` can manage a single python process
at a time.

Messages sent between client and server must be in JSON with two top level
properties: required string `type` and optional object `data`.

Command types accepted by the server are:
```
{
 "type":"[start|stop|stdin]",
 "data": {...}
}
```

Response types sent by the server are:
```
{
 "type":"[error|started|stopped|stdout|stderr]",
 "data": {...}
}
```

Command and response details:
- `start` command will start a new python process. The code to run can be specified in data as either a `souceScript` or `sourcePath` e.g.
`data: {sourceScript:"print('hi')"}` or `data: {sourcePath: "/home/pi/run.py"}`
- `started` response is sent after a successful process `start`, has no data.
<br>

- `stdin` command is used to send data to process stdin e.g. `data: { input: "this can be read by python\n"}`.
__It's important to end all input with a newline (`\n`).__
- `stdout` response is sent when process prints to stdout. e.g. `data: { output: "this was printed by python"}`
- `stderr` response is sent when process prints to stderr e.g. `data: { output: "Traceback bleh bleh"}`
<br>

- `stop` command is used to stop a running process early, has no data.
- `stopped` response is sent when a process finished and has the exit code in e.g. `data: {exitCode: 0}`
<br>

- `error` response is sent for bad commands or server errors e.g. `data: { message: "something went wrong and it's not your python code" }`

### Ideas and TODOS
- Implement `sourcePath`
- Special output formats eg image, video, graph
- Detaching, reattaching to long running programs
- Device status endpoints eg battery
- Connecction security codes displayed on OLED
- Device registration to remote server to provide easier connection
- Linking to user accounts, project workspaces & syncing
- ~~Over the internet access with reverse proxy~~

### Notes
see also https://github.com/LLK/scratch-link

![exeggcute](https://cdn.bulbagarden.net/upload/thumb/a/af/102Exeggcute.png/250px-102Exeggcute.png) ![remote](http://aux.iconspalace.com/uploads/1362096024564616892.png) ![python](https://i.pinimg.com/originals/c3/8a/8e/c38a8ed8ae5148e1441045fea19cfd20.png)
