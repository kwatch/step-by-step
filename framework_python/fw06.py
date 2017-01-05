# -*- coding: utf-8 -*-

##
## リクエストメソッドに応じて処理を変える
##
## * リクエストメソッドが GET なら、Action.GET() を呼び出す
## * リクエストメソッドが POST なら、Action.POST() を呼び出す
## * ...
##

import os


class Action(object):

    def __init__(self, environ):
        self.environ = environ
        self.status  = "200 OK"
        self.content_type = "text/html;charset=utf-8"

    def _http_405(self):
        self.status = "405 Method Not Allowed"
        return "<h2>405 Method Not Allowed</h2>"

    def GET    (self):  return self._http_405()
    def POST   (self):  return self._http_405()
    def PUT    (self):  return self._http_405()
    def DELETE (self):  return self._http_405()
    def PATCH  (self):  return self._http_405()
    def OPTIONS(self):  return self._http_405()
    def TRACE  (self):  return self._http_405()

    ## HEADメソッドは、コンテンツを何も返さない以外はGETと同じ挙動をする
    def HEAD(self):
        ## ここで返したコンテンツは、WSGI アプリケーション側で無視される
        return self.GET()


class HelloAction(Action):

    def GET(self):   # ← 変更
        return "<h1>Hello, World!</h1>"


class EnvironAction(Action):

    ## GET() を上書きしていないので、ブラウザで '/environ' にアクセスすると
    ## 405 Method Not Allowed が表示されるようになる
    def POST(self):   # ← GET ではなく POST であることに注
        environ = self.environ
        buf = []
        for key in sorted(environ.keys()):
            if key in os.environ:
                continue
            val = environ[key]
            typ = "(%s)" % type(val).__name__
            buf.append("%-25s %-7s %r\n" % (key, typ, val))
        content = "".join(buf)
        self.content_type = "text/plain;charset=utf-8"
        return content


## HTMLフォームを使って、POSTメソッドの動作を確かめる
class FormAction(Action):

    def GET(self):
        req_meth = self.environ['REQUEST_METHOD']
        html = r"""
<p>REQUEST_METHOD: %r</p>
<form method="POST" action="/form">
  <input type="submit">
</form>
"""[1:] % req_meth
        return html

    def POST(self):
        req_meth = self.environ['REQUEST_METHOD']
        html = r"""
<p>REQUEST_METHOD: %r</p>
<p><a href="/form">back</p>
""" % req_meth
        return html


class WSGIApplication(object):

    def __call__(self, environ, start_response):
        req_meth = environ['REQUEST_METHOD']  # ex: 'GET', 'POST', ...
        req_path = environ['PATH_INFO']
        if   req_path == '/hello'  : klass = HelloAction
        elif req_path == '/environ': klass = EnvironAction
        elif req_path == '/form'   : klass = FormAction  # ← 追加
        else                       : klass = None
        #
        if klass is None:
            status  = "404 Not Found"
            content = "<h2>%s</h2>" % status
            ctype   = "text/html;charset=utf-8"
        ## もしリクエストメソッドに対応したアクション関数がなければ、
        ## 405 Method Not Allowed
        elif not hasattr(klass, req_meth)
            status  = "405 Method Not Allowed"
            content = "<h2>%s</h2>" % status
            ctype   = "text/html;charset=utf-8"
        ## そうでなければ、アクション関数を呼び出す
        else:
            func    = getattr(klass, req_meth)
            action  = klass(environ)
            content = func(action)
            status  = action.status       # ex: '200 OK'
            ctype   = action.content_type
        ## HEAD メソッドの場合は、コンテンツを空にする
        if req_meth == 'HEAD':
            content = ""
        #
        headers = [
            ('Content-Type', ctype),
        ]
        start_response(status, headers)
        return [content.encode('utf-8')]


wsgi_app = WSGIApplication()


if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    wsgi_server = make_server('localhost', 7000, wsgi_app)
    wsgi_server.serve_forever()
