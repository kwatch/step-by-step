# -*- coding: utf-8 -*-

##
## WSGI アプリケーションをクラスにする
##


class WSGIApplication(object):

    ## オブジェクトをあたかも関数のように呼び出すためのメソッド
    ## (注: Pythonでは obj.__call__() を obj() と書ける)
    def __call__(self, environ, start_response):
        content = "<h1>Hello, World!</h1>"
        status = "200 OK"
        headers = [
            ('Content-Type', 'text/html;charset-utf8'),
        ]
        start_response(status, headers)
        return [content.encode('utf-8')]


## リクエスト情報が入った辞書オブジェクト(environ)を受け取り、
## レスポンスを返すWSGIアプリケーションオブジェクト
wsgi_app = WSGIApplication()


if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    wsgi_server = make_server('localhost', 7000, wsgi_app)
    wsgi_server.serve_forever()
