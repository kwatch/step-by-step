# -*- coding: utf-8 -*-

##
## HTTP リクエストの中身を表示する
##

import os


## environ は、HTTP リクエスト情報が格納された辞書。
## start_response は、レスポンス開始時に呼び出す関数。
def wsgi_app(environ, start_response):
    ## environ の内容 (キーと値) を一覧表示
    buf = []
    for key in sorted(environ.keys()):
        ## 注: wsgiref の HTTP サーバだと、環境変数の内容が
        ## environ に混ざるので、それらを表示しない
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


if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    wsgi_server = make_server('localhost', 7000, wsgi_app)
    wsgi_server.serve_forever()
