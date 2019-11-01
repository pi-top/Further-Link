# ~diglett~ ~webide-~ * further-link * ~jv-rover-pi-client-connector~
flask-sockets server for executing python code and accessing stdin/out/err
streams over websockets.
~like pokemon diglett, it can make a tunnel from client to server~

![exeggcute](https://cdn.bulbagarden.net/upload/thumb/a/af/102Exeggcute.png/250px-102Exeggcute.png) ![remote](http://aux.iconspalace.com/uploads/1362096024564616892.png) ![python](https://i.pinimg.com/originals/c3/8a/8e/c38a8ed8ae5148e1441045fea19cfd20.png)

see also https://github.com/LLK/scratch-link

### Usage
We are using [pipenv](https://github.com/pypa/pipenv) for dependencies
```
pipenv shell
pipenv sync
python3 run.py
```

### Websocket API
Each connected websocket client can manage a single python process.
```
ws://ip:[port]/exec
```

Commands:
```
{
 "type":"[start|stop|stdin]",
 "data": {...}
}
```
Responses:
```
{
 "type":"[error|started|stopped|stdout|stderr]",
 "data": {...}
}
```

server or command errors will return a `error` type response with eg `data: { message: "something went wrong and it's not python code" }`

`start` command will start a new python process. The code to run can be specified in data by either `data: {sourceScript:"print('hi')"}` or `data: {sourcePath: "/home/pi/run.py"}`
`started` response does not have data.

`stdin` command has `data: { input: "this can be read by python\n"}`. *NB* It's
important to end all input with a newline (`\n`).
`stdout` response has data: { output: "this was printed by python"}

`stop` command has no data
`stopped` response returns the exit code int `data: {exitCode: 0}`

python errors will trigger a `stderr` response with `data: { output: "Traceback bleh bleh"}}`

#### Example usage:
- Connect to websocket on /exec: `websocat ws://localhost:8500/exec`
- Input start command: `{"type":"start","data":{"sourceScript":"print('hi')"}}`
- Recieve response on websocket: `{"type":"stdout","data":"hi\n"}`

### HTTP API
```
/status => :ok_hand:
```

