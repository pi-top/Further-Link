from src import app

if __name__ == "__main__":
  from gevent import pywsgi
  from geventwebsocket.handler import WebSocketHandler

  server = pywsgi.WSGIServer(('127.0.0.1', 8080), app, handler_class=WebSocketHandler)
  server.serve_forever()
