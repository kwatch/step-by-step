# -*- coding: utf-8 -*-

##
## WSGI アプリケーションを関数からオブジェクトに変更する
##

import os


class WSGIApplication(object):

    ## オブジェクトをあたかも関数のように呼び出すためのメソッド
    ## (注: Python では obj.__call__(x) を obj(x) と書ける)
    def __call__(self, environ, start_response):
        content = self._render_content(environ)
        #
        status = "200 OK"
        headers = [
            ('Content-Type', 'text/plain;charset-utf8'),
        ]
        start_response(status, headers)
        return [content.encode('utf-8')]

    ## コンテンツ生成機能を別メソッドに分離する
    def _render_content(self, environ):
        buf = []
        for key in sorted(environ.keys()):
            if key in os.environ:
                continue
            val = environ[key]
            typ = "(%s)" % type(val).__name__
            buf.append("%-25s %5s %r\n" % (key, typ, val))
        content = "".join(buf)
        return content


## これはオブジェクトであるが、関数と同じように呼び出せる
## (＝ wsgi_app(environ, start_response) として呼び出せる)。
## そのため、今までの関数と同じように扱える。
wsgi_app = WSGIApplication()


if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    wsgi_server = make_server('localhost', 7000, wsgi_app)
    wsgi_server.serve_forever()
