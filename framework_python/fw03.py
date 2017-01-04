# -*- coding: utf-8 -*-

##
## HTTPリクエストの中身を表示する
## TODO: 環境変数が表示されないよう、waitressを使うべきか？
##

from html import escape as h


class WSGIApplication(object):

    def __call__(self, environ, start_response):
        ## environ (HTTPリクエスト情報が格納された辞書) の
        ## 内容 (キーと値) をHTMLテーブルで表示する
        buf = []; add = buf.append
        add("<table border=1 cellspacing=0 cellpadding=2>")
        add("<tr>")
        add("  <th>Key</th>")
        add("  <th>Type</th>")   # 値の型名 (str, boolなど) も表示
        add("  <th>Value</th>")
        add("</tr>")
        for key in sorted(environ.keys()):
            val = environ[key]
            add("<tr>")
            add("  <td><b>%s</b></td>" % h(key))
            add("  <td><i>%s</i></td>" % h(type(val).__name__))
            add("  <td><tt>%s</tt></td>" % h(str(val)))
            add("</tr>")
        add("</table>")
        content = "\n".join(buf)
        #
        status = "200 OK"
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
