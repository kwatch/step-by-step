# -*- coding: utf-8 -*-

##
## subject: コンテンツの生成を専用のクラスに任せる
##

import os


class EnvironAction(object):

    def __init__(self, environ):
        self.environ = environ

    ## コンテンツを生成する
    def run(self):
        environ = self.environ     # ← 追加
        buf = []
        for key in sorted(environ.keys()):
            if key in os.environ:
                continue
            val = environ[key]
            typ = "(%s)" % type(val).__name__
            buf.append("%-25s %-7s %r\n" % (key, typ, val))
        content = "".join(buf)
        return content


class WSGIApplication(object):

    def __call__(self, environ, start_response):
        ## コンテンツの生成をActionクラスに任せる
        action = EnvironAction(environ)
        content = action.run()
        #
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
