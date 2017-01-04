# -*- coding: utf-8 -*-

##
## HTTPリクエストの中身を表示する
## TODO: 環境変数が表示されないよう、waitressを使うべきか？
##

import os


class WSGIApplication(object):

    def __call__(self, environ, start_response):
        ## environ (HTTPリクエスト情報が格納された辞書) の
        ## 内容 (キーと値) を一覧表示
        buf = []
        for key in sorted(environ.keys()):
            ## 注: wsgirefのHTTPサーバだと、環境変数の内容が
            ## environに混ざるので、環境変数を除いて表示する
            if key in os.environ:
                continue
            ## キーと、値の型と、値を、一行ずつ表示
            val = environ[key]
            typ = "(%s)" % type(val).__name__
            buf.append("%-25s %5s %r\n" % (key, typ, val))
        content = "".join(buf)
        ## text/html ではなく text/plain で表示
        status = "200 OK"
        headers = [
            ('Content-Type', 'text/plain;charset-utf8'),
        ]
        start_response(status, headers)
        return [content.encode('utf-8')]


wsgi_app = WSGIApplication()


if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    wsgi_server = make_server('localhost', 7000, wsgi_app)
    wsgi_server.serve_forever()
