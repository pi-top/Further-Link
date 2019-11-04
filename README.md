# further-link
This project is intended to run on a pi-top[4], to allow connecting to the
revice from [Further](further.pi-top.com).

The primary use case of this is to remotely run user's code (python3) on the
pi-top. A websocket api is provided to start and stop python programs and
access their stdin/out/err streams.

![exeggcute](https://cdn.bulbagarden.net/upload/thumb/a/af/102Exeggcute.png/250px-102Exeggcute.png) ![remote](http://aux.iconspalace.com/uploads/1362096024564616892.png) ![python](https://i.pinimg.com/originals/c3/8a/8e/c38a8ed8ae5148e1441045fea19cfd20.png)

see also https://github.com/LLK/scratch-link

### Usage
We are using Python 3.7 and managing dependencies with
[pipenv](https://github.com/pypa/pipenv)
```
pipenv shell
pipenv sync
python3 run.py
```

The default port, __8028__, can be changed by setting FURTHER_LINK_PORT env
variable.
```
curl http://[IP]:[PORT]/status # 200 OK
```

### Websocket API
Each websocket client connected on `/exec` can manage a single python process.
```
websocat ws://[IP]:[PORT]/exec
```

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
- `start`: command will start a new python process. The code to run can be specified in data as either a `souceScript` or `sourcePath` e.g.
`data: {sourceScript:"print('hi')"}` or `data: {sourcePath: "/home/pi/run.py"}`
- `started`: response will be sent after a successful process `start`, has no data.

- `stdin`: command is used to send data to process stdin e.g. `data: { input: "this can be read by python\n"}`.
*NB* It's important to end all input with a newline (`\n`).
- `stdout`: response sent when process prints to stdout. e.g. `data: { output: "this was printed by python"}`
- `stderr`: response sent when process prints to stderr e.g. `data: { output: "Traceback bleh bleh"}`

- `stop`: command is used to stop a running process early, has no data.
- `stopped`: response is sent when a process finished and has the exit code in e.g. `data: {exitCode: 0}`

- `error`: response will be sent for bad commands or server errors e.g. `data: { message: "something went wrong and it's not your python code" }`

#### Example usage:
- Connect to websocket on /exec: `websocat ws://localhost:8500/exec`
- Input start command: `{"type":"start","data":{"sourceScript":"print('hi')"}}`
- Recieve response on websocket: `{"type":"stdout","data":"hi\n"}`
