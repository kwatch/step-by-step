# -*- coding: utf-8 -*-

##
## subject: URLパスパターンとアクションクラスとのマッピングをリストにする
##

import os
import json


class Request(object):

    def __init__(self, environ):
        self.environ = environ
        self.method  = environ['REQUEST_METHOD']
        self.path    = environ['PATH_INFO']


class Response(object):

    def __init__(self):
        self.status  = "200 OK"
        self.headers = {
            'Content-Type': "text/html;charset=utf-8",
        }

    def header_list(self):
        return [ (k, v) for k, v in self.headers.items() ]

    @property
    def content_type(self):
        return self.headers['Content-Type']

    @content_type.setter
    def content_type(self, value):
        self.headers['Content-Type'] = value


class BaseAction(object):

    def __init__(self, req, resp):
        self.req  = req
        self.resp = resp

    def before_action(self):
        pass

    def after_action(self, ex):
        pass

    def invoke_action(self, func):
        content = func(self)
        return content

    def handle_action(self, func):
        ex = None
        try:
            self.before_action()
            return self.invoke_action(func)
        except Exception as ex_:
            ex = ex_
            raise
        finally:
            self.after_action(ex)


class Action(BaseAction):

    def invoke_action(self, func):
        content = BaseAction.invoke_action(self, func)
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False)
            self.resp.content_type = "application/json"
        return content

    def _http_405(self):
        self.resp.status = "405 Method Not Allowed"
        return "<h2>405 Method Not Allowed</h2>"

    def GET    (self):  return self._http_405()
    def POST   (self):  return self._http_405()
    def PUT    (self):  return self._http_405()
    def DELETE (self):  return self._http_405()
    def PATCH  (self):  return self._http_405()
    def OPTIONS(self):  return self._http_405()
    def TRACE  (self):  return self._http_405()

    def HEAD(self):
        return self.GET()


HTTP_REQUEST_METHODS = {'GET', 'POST', 'PUT', 'DELETE', 'HEAD',
                        'PATCH', 'OPTIONS', 'TRACE'}
assert HTTP_REQUEST_METHODS == { s for s in dir(Action) if s.isupper() }


class HelloAction(Action):

    def GET(self):
        return {"message": "Hello, World!"}


class EnvironAction(Action):

    def GET(self):
        environ = self.req.environ
        buf = []
        for key in sorted(environ.keys()):
            if key in os.environ:
                continue
            val = environ[key]
            typ = "(%s)" % type(val).__name__
            buf.append("%-25s %-7s %r\n" % (key, typ, val))
        content = "".join(buf)
        self.resp.content_type = "text/plain;charset=utf-8"
        return content


class FormAction(Action):

    def GET(self):
        req_meth = self.req.method
        html = ('<p>REQUEST_METHOD: %r</p>\n'
                '<form method="POST" action="/form">\n'
                '<input type="submit">\n'
                '</form>\n')
        return html % req_meth

    def POST(self):
        req_meth = self.req.method
        html = ('<p>REQUEST_METHOD: %r</p>\n'
                '<p><a href="/form">back</p>\n')
        return html % req_meth


## URLパスパターンとアクションクラスの、マッピングリスト
mapping_list = [
    ('/hello'    , HelloAction),
    ('/environ'  , EnvironAction),
    ('/form'     , FormAction),
]


class WSGIApplication(object):

    def __init__(self, mapping_list):
        self._mapping_list = mapping_list

    def lookup(self, req_path):
        for urlpath, klass in self._mapping_list:
            if req_path == urlpath:
                return klass
        return None

    def __call__(self, environ, start_response):
        req  = Request(environ)
        resp = Response()
        #
        req_meth = req.method
        req_path = req.path
        klass = self.lookup(req_path)
        #
        if klass is None:
            status  = "404 Not Found"
            content = "<h2>%s</h2>" % status
        elif req_meth not in HTTP_REQUEST_METHODS:
            status  = "405 Method Not Allowed"
            content = "<h2>%s</h2>" % status
        else:
            func    = getattr(klass, req_meth)
            action  = klass(req, resp)
            content = action.handle_action(func)
            status  = resp.status
        if req_meth == 'HEAD':
            content = ""
        #
        headers = resp.header_list()
        start_response(status, headers)
        return [content.encode('utf-8')]


## WSGI アプリケーション作成時に、マッピングリストを渡す
wsgi_app = WSGIApplication(mapping_list)


if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    wsgi_server = make_server('localhost', 7000, wsgi_app)
    wsgi_server.serve_forever()
