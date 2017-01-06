# -*- coding: utf-8 -*-

##
## subject: URLパスパラメータをサポート
##

import os
import re
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

    def invoke_action(self, func, kwargs):   # ← 変更
        content = func(self, **kwargs)       # ← 変更
        return content

    def handle_action(self, func, kwargs):   # ← 変更
        ex = None
        try:
            self.before_action()
            return self.invoke_action(func, kwargs)
        except Exception as ex_:
            ex = ex_
            raise
        finally:
            self.after_action(ex)


class Action(BaseAction):

    def invoke_action(self, func, kwargs):    # ← 変更
        content = BaseAction.invoke_action(self, func, kwargs) # ← 変更
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False)
            self.resp.content_type = "application/json"
        return content

    def _http_405(self):
        self.resp.status = "405 Method Not Allowed"
        return "<h2>405 Method Not Allowed</h2>"

    def GET    (self, **kwargs):  return self._http_405()
    def POST   (self, **kwargs):  return self._http_405()
    def PUT    (self, **kwargs):  return self._http_405()
    def DELETE (self, **kwargs):  return self._http_405()
    def PATCH  (self, **kwargs):  return self._http_405()
    def OPTIONS(self, **kwargs):  return self._http_405()
    def TRACE  (self, **kwargs):  return self._http_405()

    def HEAD(self, **kwargs):
        return self.GET(**kwargs)


HTTP_REQUEST_METHODS = {'GET', 'POST', 'PUT', 'DELETE', 'HEAD',
                        'PATCH', 'OPTIONS', 'TRACE'}
assert HTTP_REQUEST_METHODS == { s for s in dir(Action) if s.isupper() }


class HelloAction(Action):

    def GET(self, name):             # ← 変更
        msg = "Hello, %s" % name     # ← 変更
        return {"message": msg}      # ← 変更


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


mapping_list = [
    ('/hello/{name}', HelloAction),  # ← 変更
    ('/environ'  , EnvironAction),
    ('/form'     , FormAction),
]


## URLパスパターンを正規表現に変換する。
## 例: '/api/foo/{id}.json' → '^/api/foo/(?P<id>[^/]+)\\.json$'
def _convert_urlpath(urlpath):   # ex: '/api/foo/{id}.json'
    def _re_escape(string):
        return re.escape(string).replace(r'\/', '/')
    #
    buf = ['^']; add = buf.append
    pos = 0
    for m in re.finditer(r'(.*?)\{(.*?)\}', urlpath):
        pos = m.end(0)                   # ex: 13
        string, param_name = m.groups()  # ex: ('/api/foo/', 'id')
        if not param_name.isidentifier():
            raise ValueError("'{%s}': invalid parameter (in '%s')" \
                                 % (param_name, urlpath))
        add(_re_escape(string))
        add('(?P<%s>[^/]+)' % param_name)  # ex: '(?P<id>[^/]+)'
    remained = urlpath[pos:]  # ex: '.json'
    add(_re_escape(remained))
    add('$')
    return "".join(buf)   # ex: '^/api/foo/(?P<id>[^/]+)\\.json$'


class WSGIApplication(object):

    def __init__(self, mapping_list):
        new_list = []
        self._build(mapping_list, new_list)
        self._mapping_list = new_list

    def _build(self, mapping_list, new_list):
        for urlpath, klass in mapping_list:
            rexp = re.compile(_convert_urlpath(urlpath))
            t = (urlpath, rexp, klass)
            new_list.append(t)

    def lookup(self, req_path):
        ## リクエストパスに対応した Action クラスに加え、
        ## URLパスパラメータの値も返す
        for _, rexp, klass in self._mapping_list:
            m = rexp.match(req_path)
            if m:
                kwargs = m.groupdict()  # ex: {"id": 123}
                return klass, kwargs    # ex: UserAction, {"id": 123}
        return None, None

    def __call__(self, environ, start_response):
        req  = Request(environ)
        resp = Response()
        #
        req_meth = req.method
        req_path = req.path
        klass, kwargs = self.lookup(req_path)  # ← 変更
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
            content = action.handle_action(func, kwargs) # ← 変更
            status  = resp.status
        if req_meth == 'HEAD':
            content = ""
        #
        headers = resp.header_list()
        start_response(status, headers)
        return [content.encode('utf-8')]


wsgi_app = WSGIApplication(mapping_list)


if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    wsgi_server = make_server('localhost', 7000, wsgi_app)
    wsgi_server.serve_forever()
