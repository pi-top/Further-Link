# ~diglett~ ~jv-rover-webide~ further-link ~pi-client-connector~
this is python project like pokemon diglett,it can make a tunnel from client to server and runing code,register to cloud,check status and do more coding things.

# Usage

 Before running install flask  modules using:
 ```
  pip install -r requirements.txt
 ```
 if your pyton3 but pip is pip3 you should useing:
 ```
   pip3 install -r requirements.txt
 ```

 To start production use:
 ```
  python3 run.py
 ```

The Api you can use swagger show them,when you running it,if you are not change the default
port it should be [80] or [5000] port
you can try :
  ```
   http://ip:[80|5000]/api/
  ```


# API
### Battery
battery check

GET /battery/

```
    curl -X GET "http://ip:[port]/api/battery/" -H "accept: application/json"
```
```
    {
      "info": "success",
      "code": "0000",
      "data": {
        "state": "FullyCharged",
        "capacity": "100"
      },
      "success": true
    }
```


### Execute Code
init project files

POST /exec/
```
    curl -X POST "http://ip:[port]/api/exec/" -H "accept: application/json" -H "Content-Type: application/json" -d "[ { \"projectVersionId\": \"string\", \"path\": \"string\", \"content\": \"string\", \"id\": \"string\" }]"
```
```
    {
      "info": "success",
      "code": "0000",
      "data": null,
      "success": true
    }
```

### Websocket
this  ws api for running code

```
     ws://ip:[port]/ws/exec

     Data:

     {
       "cmd":"[start|stop|input]",
       "projectVersionId":"xxxxx",
       "data":"xxx/xxxx/sss.py | ps -ef"
      }
```


