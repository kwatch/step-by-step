# -*- coding: utf-8 -*-

##
## subject: URLパスパラメータの正規表現をサポート
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

    def invoke_action(self, func, kwargs):
        content = func(self, **kwargs)
        return content

    def handle_action(self, func, kwargs):
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

    def invoke_action(self, func, kwargs):
        content = BaseAction.invoke_action(self, func, kwargs)
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

    def GET(self, name):
        msg = "Hello, %s" % name
        return {"message": msg}


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
    ('/hello/{name:str<[A-Z][a-z]*>}', HelloAction),  # ← 変更
    ('/environ'  , EnvironAction),
    ('/form'     , FormAction),
]


## URLパスパターンを正規表現に変換する。
##   例: '/foo/{id}.json'   → '^/foo/(?P<id>[^/]+)\\.json$'
## URLパスパラメータには正規表現を指定できる。
##   例: '/js/{path:<.+>}'  → '^/js/(?P<path>.+)$'
##       '/foo/{id:<\d+>}'  → '^/foo/(?P<id>\d+)$'
## 正規表現のかわりにデータ型 (str, int) を指定できる。
## その場合、str型なら [^/]+ が、int型なら \d+ が使われる。
## なお文字列を整数に変換するといったことはしない。
##   例: '/foo/{id:str}'    → '^/foo/(?P<id>[^/]+)$'
##       '/foo/{id:int}'    → '^/foo/(?P<id>\d+)$'
## データ型と正規表現の両方を指定した場合は、後者が使われる。
##   例: '/{id:int<\d{3}>}' → '^/(?P<id>\d{3})$'
## 両方を省略した場合は、str型として扱われる。
##   例: '/foo/{id}'        → '^/foo/(?P<id>[^/]+)$'
def _convert_urlpath(urlpath):   # ex: '/api/foo/{id}.json'
    def _re_escape(string):
        return re.escape(string).replace(r'\/', '/')
    #
    param_rexps = {'str': r'[^/]+', 'int': r'\d+'}
    buf = ['^']; add = buf.append
    pos = 0
    for m in re.finditer(r'(.*?)\{(\w+)(:\w*)?(<[^>]*>)?\}', urlpath):
        pos = m.end(0)                   # ex: 13
        string, pname, ptype, prexp = m.groups()  # ex: ('/api/foo/', 'id')
        if ptype: ptype = ptype[1:]      # ex: ':int' -> 'int'
        if prexp: prexp = prexp[1:-1]    # ex: '<\d+>' -> '\d+'
        #
        if not ptype:
            ptype = 'str'        # デフォルトは str 型
        if ptype not in param_rexps:
            raise ValueError("%r: contains unknown data type %r." \
                                 % (urlpath, ptype))
        if not prexp:
            prexp = param_rexps[ptype]  # デフォルトの正規表現
        #
        add(_re_escape(string))
        add('(?P<%s>%s)' % (pname, prexp))  # ex: '(?P<id>[^/]+)'
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
        klass, kwargs = self.lookup(req_path)
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
            content = action.handle_action(func, kwargs)
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
