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

    def HEAD(self):
        ## HEADメソッドは、コンテンツを何も返さない以外はGETと同じ挙動をする。
        ## そのため、self.GET() を呼び出すが返されたコンテンツは無視する。
        self.GET()
        return ""


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
        req_meth = environ['REQUEST_METHOD']   # ← 追加
        req_path = environ['PATH_INFO']
        if req_path == '/hello':
            klass = HelloAction
        elif req_path == '/environ':
            klass = EnvironAction
        elif req_path == '/form':   # ← 追加
            klass = FormAction      # ← 追加
        else:
            klass = None
        #
        if klass:
            ## リクエストメソッドに応じたインスタンスメソッドを呼び出す
            ## (TODO: 本当は他のリクエストメソッドもあり得る)
            assert req_meth in ('GET', 'POST', 'PUT', 'DELETE', 'PATCH',
                                'OPTIONS', 'TRACE', 'HEAD')
            action = klass(environ)
            func = getattr(action, req_meth)  # インスタンスメソッドを取り出して
            content = func()                  # 呼び出す
            status = action.status  # ex: '200 OK' or '405 Method Not Allowed'
            ctype  = action.content_type
        else:
            status  = "404 Not Found"
            content = "<h2>%s</h2>" % status
            ctype   = "text/html;charset=utf-8"
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
