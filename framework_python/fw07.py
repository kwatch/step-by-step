# -*- coding: utf-8 -*-

##
## RequestクラスとResponseクラスを作る
##

import os


## HTTPリクエストを表すクラス
class Request(object):

    def __init__(self, environ):
        self.environ = environ
        self.method  = environ['REQUEST_METHOD']
        self.path    = environ['PATH_INFO']


## HTTPレスポンスを表すクラス
class Response(object):

    def __init__(self):
        self.status  = "200 OK"
        self.headers = {
            'Content-Type': "text/html;charset=utf-8",
        }

    def header_list(self):
        ## ヘッダーの辞書を、タプルのリストに変換する
        return [ (k, v) for k, v in self.headers.items() ]

    @property
    def content_type(self):
        return self.headers['Content-Type']

    @content_type.setter
    def content_type(self, value):
        self.headers['Content-Type'] = value


class Action(object):

    ## リクエストとレスポンスを受け取る
    def __init__(self, req, resp):
        self.req  = req
        self.resp = resp

    def _http_405(self):
        self.resp.status = "405 Method Not Allowed"  # ← 変更
        return "<h2>405 Method Not Allowed</h2>"

    def GET    (self):  return self._http_405()
    def POST   (self):  return self._http_405()
    def PUT    (self):  return self._http_405()
    def DELETE (self):  return self._http_405()
    def PATCH  (self):  return self._http_405()
    def OPTIONS(self):  return self._http_405()
    def TRACE  (self):  return self._http_405()

    def HEAD(self):
        return self.GET()


class HelloAction(Action):

    def GET(self):
        return "<h1>Hello, World!</h1>"


class EnvironAction(Action):

    def GET(self):   # ← GETに変更
        environ = self.req.environ  # ← 変更
        buf = []
        for key in sorted(environ.keys()):
            if key in os.environ:
                continue
            val = environ[key]
            typ = "(%s)" % type(val).__name__
            buf.append("%-25s %-7s %r\n" % (key, typ, val))
        content = "".join(buf)
        self.resp.content_type = "text/plain;charset=utf-8"  # ← 変更
        return content


class FormAction(Action):

    def GET(self):
        req_meth = self.req.method  # ← 変更
        html = r"""
<p>REQUEST_METHOD: %r</p>
<form method="POST" action="/form">
  <input type="submit">
</form>
"""[1:] % req_meth
        return html

    def POST(self):
        req_meth = self.req.method  # ← 変更
        html = r"""
<p>REQUEST_METHOD: %r</p>
<p><a href="/form">back</p>
""" % req_meth
        return html


class WSGIApplication(object):

    def __call__(self, environ, start_response):
        ## リクエストとレスポンスのオブジェクトを作る
        req  = Request(environ)
        resp = Response()
        #
        req_meth = req.method          # ← 変更
        req_path = req.path            # ← 変更
        if   req_path == '/hello'  : klass = HelloAction
        elif req_path == '/environ': klass = EnvironAction
        elif req_path == '/form'   : klass = FormAction
        else                       : klass = None
        #
        if klass is None:
            status  = "404 Not Found"
            content = "<h2>%s</h2>" % status
        else:
            action = klass(req, resp)  # ← 変更
            func = getattr(action, req_meth, None)
            if func is None:
                status  = "405 Method Not Allowed"
                content = "<h2>%s</h2>" % status
            else:
                content = func()
                status  = resp.status  # ← 変更
        if req_meth == 'HEAD':
            content = ""
        #
        headers = resp.header_list()   # ← 変更
        start_response(status, headers)
        return [content.encode('utf-8')]


wsgi_app = WSGIApplication()


if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    wsgi_server = make_server('localhost', 7000, wsgi_app)
    wsgi_server.serve_forever()
