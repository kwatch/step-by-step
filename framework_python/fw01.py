# -*- coding: utf-8 -*-

##
## subject: はじめての WSGI アプリケーション
##


## リクエスト情報が入った辞書オブジェクト(environ)を受け取り、
## レスポンスを返すWSGIアプリケーション関数
def wsgi_app(environ, start_response):
    ## コンテンツを用意する
    content = "<h1>Hello, World!</h1>"
    ## レスポンスのステータスとヘッダーを用意する
    status = "200 OK"
    headers = [
        ('Content-Type', 'text/html;charset-utf8'),
    ]
    ## レスポンスを開始する
    start_response(status, headers)
    ## レスポンスボディとして、バイナリのリストを返す
    return [content.encode('utf-8')]


if __name__ == "__main__":
    ## http://localhost:7000/ にアクセスするとコンテンツが表示される
    from wsgiref.simple_server import make_server
    wsgi_server = make_server('localhost', 7000, wsgi_app)
    wsgi_server.serve_forever()
