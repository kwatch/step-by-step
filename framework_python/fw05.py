# -*- coding: utf-8 -*-

##
## リクエストパスに応じて、異なるコンテンツを返す
##
## * http://localhost:7000/hello なら、Hello World を表示
## * http://localhost:7000/environ なら、environの内容を表示
## * それ以外なら、404 Not Found を表示
##

import os


## すべてのActionクラスの親クラス
class Action(object):

    def __init__(self, environ):
        self.environ = environ
        self.content_type = "text/html;charset=utf-8"

    def run(self):   # 子クラスでこのメソッドを上書きする
        raise NotImplementedError()


## '/hello' に対応したActionクラス
class HelloAction(Action):

    def run(self):   # 上書き
        return "<h1>Hello, World!</h1>"


## '/environ' に対応したActionクラス
class EnvironAction(Action):

    def run(self):   # 上書き
        environ = self.environ
        buf = []
        for key in sorted(environ.keys()):
            if key in os.environ:
                continue
            val = environ[key]
            typ = "(%s)" % type(val).__name__
            buf.append("%-25s %-7s %r\n" % (key, typ, val))
        content = "".join(buf)
        self.content_type = "text/plain;charset=utf-8" # ← 追加
        return content


class WSGIApplication(object):

    def __call__(self, environ, start_response):
        ## リクエストパスに対応したActionクラスを探す
        req_path = environ['PATH_INFO']
        if req_path == '/hello':
            klass = HelloAction
        elif req_path == '/environ':
            klass = EnvironAction
        else:
            klass = None
        ## Actionクラスがあれば、コンテンツを生成する
        if klass:
            action  = klass(environ)
            content = action.run()
            status  = "200 OK"
            ctype   = action.content_type
        ## Actionクラスがなければ、404 Not Found を表示する
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
