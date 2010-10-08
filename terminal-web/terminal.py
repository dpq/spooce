#!/usr/bin/python
# -*- coding: utf-8 -*-
from gevent import monkey; monkey.patch_socket()
from gevent.wsgi import WSGIServer

from werkzeug import Request, Response
import logging, memcache, os


class Terminal(object):
    def __init__(self):
        self.mc = memcache.Client(['127.0.0.1:11211'], debug=0)

    def __file(self, path):
        body = open(path, 'rb').read()
        return body

    def __call__(self, env, start_response):
        req = Request(env)
        resp = Response(status=200)
        if req.path == '/':
            resp.content_type = "text/html"
            resp.response = [self.__file('index.html')]
            return resp(env, start_response)
        elif req.path == '/favicon.gif':
            resp.content_type = "image/gif"
            resp.response = [self.__file('favicon.gif')]
            return resp(env, start_response)
        elif req.path.startswith('/script/'):
            try:
                resp.response = [self.__file(req.path.replace('/script/', ''))]
                resp.content_type = "text/javascript"
                return resp(env, start_response)
            except:
                resp.status_code = 404
                resp.content_type = "text/plain"
                resp.response = [""]
                return resp(env, start_response)
        else:
            resp.status_code = 404
            resp.response = [""]
            return resp(env, start_response)


def main():
    address = ("0.0.0.0", 8081)
    server = WSGIServer(address, Terminal())
    try:
        logging.info("Server running on port %s:%d. Ctrl+C to quit" % address)
        server.serve_forever()
    except KeyboardInterrupt:
        server.stop()
        logging.info("Server stopped")


if __name__ == "__main__":
    main()
