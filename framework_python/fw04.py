# -*- coding: utf-8 -*-

##
## コンテンツの生成を専用のクラスに任せる
##

from html import escape as h


class TableAction(object):

    def __init__(self, environ):
        self.environ = environ

    ## コンテンツを生成する
    def run(self):
        environ = self.environ     # ← 追加
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
        ## コンテンツの生成をActionクラスに任せる
        action = TableAction(environ)
        content = action.run()
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
