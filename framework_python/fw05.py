# -*- coding: utf-8 -*-

##
## リクエストパスに応じて、異なるコンテンツを返す
##
## * http://localhost:7000/hello なら、Hello World を表示
## * http://localhost:7000/table なら、HTMLテーブルを表示
## * それ以外なら、404 Not Found を表示
##

from html import escape as h


## すべてのActionクラスの親クラス
class Action(object):

    def __init__(self, environ):
        self.environ = environ

    def run(self):   # 子クラスでこのメソッドを上書きする
        raise NotImplementedError()


## '/hello' に対応したActionクラス
class HelloAction(Action):

    def run(self):   # 上書き
        return "<h1>Hello, World!</h1>"


## '/table' に対応したActionクラス
class TableAction(Action):

    def run(self):   # 上書き
        environ = self.environ
        buf = []; add = buf.append
        add("<table border=1 cellspacing=0 cellpadding=2>")
        add("<tr>")
        add("  <th>Key</th>")
        add("  <th>Type</th>")
        add("  <th>Value</th>")
        add("</tr>")
        for key in sorted(self.environ.keys()):
            val = environ[key]
            add("<tr>")
            add("  <td><b>%s</b></td>" % h(key))
            add("  <td><i>%s</i></td>" % h(type(val).__name__))
            add("  <td><tt>%s</tt></td>" % h(str(val)))
            add("</tr>")
        add("</table>")
        content = "\n".join(buf)
        return content


class WSGIApplication(object):

    def __call__(self, environ, start_response):
        ## リクエストパスに対応したActionクラスを探す
        req_path = environ['PATH_INFO']
        if req_path == '/hello':
            klass = HelloAction
        elif req_path == '/table':
            klass = TableAction
        else:
            klass = None
        ## Actionクラスがあれば、コンテンツを生成する
        if klass:
            action = klass(environ)
            content = action.run()
            status = "200 OK"
        ## Actionクラスがなければ、404 Not Found を表示する
        else:
            status = "404 Not Found"
            content = "<h2>%s</h2>" % h(status)
        #
        headers = [
            ('Content-Type', 'text/html;charset-utf8'),
        ]
        start_response(status, headers)
        return [content.encode('utf-8')]


wsgi_app = WSGIApplication()


if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    wsgi_server = make_server('localhost', 7000, wsgi_app)
    wsgi_server.serve_forever()
