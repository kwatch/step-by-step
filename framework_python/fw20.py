# -*- coding: utf-8 -*-

##
## subject: クエリパラメータとフォームパラメータのパースを実装
##

import sys
import os
import re
import json
from urllib.parse import unquote_plus
from html import escape as h


class Request(object):

    def __init__(self, environ):
        self.environ = environ
        self.method  = environ['REQUEST_METHOD']
        self.path    = environ['PATH_INFO']

    @property
    def query_string(self):
        return self.environ['QUERY_STRING']

    @property
    def content_type(self):
        return self.environ['CONTENT_TYPE']

    @property
    def content_length(self):
        s = self.environ['CONTENT_LENGTH']
        return int(s) if s else None

    @property
    def query(self):
        if not hasattr(self, '_query'):
            self._query = _parse_query_str(self.query_string)
        return self._query

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._form = _parse_query_str(self._read_input())
        return self._form

    @property
    def json(self):
        if not hasattr(self, '_json'):
            self._json = json.loads(self._read_input())
        return self._json

    def _read_input(self):
        input   = self.environ['wsgi.input']
        binary  = input.read(self.content_length)
        unicode = binary.decode('utf-8')
        return unicode


def _parse_query_str(query_str):
    d = {}
    if not query_str:
        return d
    unq = unquote_plus
    ss = query_str.split('&') # ex: 'x=1&y=2' -> ['x=1', 'y=2']
    for s in ss:
        kv = s.split('=', 1)  # ex: 'x=1' -> ['x', '1']; 'x' -> ['x']
        if len(kv) == 2:
            k, v = kv
        else:
            k = kv[0]; v = ""
        k = unq(k); v = unq(v)
        if k.endswith('[]'):
            d.setdefault(k, []).append(v)
        else:
            d[k] = v
    return d


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


def on(req_meth, urlpath):
    localvars = sys._getframe(1).f_locals
    mapping = localvars.setdefault('__mapping__', [])
    for upath, funcs in mapping:
        if upath == urlpath:
            break
    else:
        funcs = {}
        mapping.append((urlpath, funcs))
    if req_meth in funcs:
        raise ValueError("@on(%r, %r): duplicated." % (req_meth, urlpath))
    def deco(func):
        funcs[req_meth] = func
        return func
    return deco


class HelloAction(Action):

    ITEMS = [
        {"name": "Alice"},
        {"name": "Bob"},
        {"name": "Charlie"},
    ]

    @on('GET', r'.json')
    def do_index(self):
        return {
            "items": self.ITEMS,
        }

    @on('GET', r'/{name:<\w+>}.json')
    def do_show(self, name):
        for x in self.ITEMS:
            if x['name'] == name:
                break
        else:
            self.resp.status = "404 Not Found"
            return {"error": "404 Not Found"}
        msg = "Hello, %s!" % name
        return {"message": msg}


class EnvironAction(Action):

    @on('GET', r'')
    def do_render(self):
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

    @on('GET', r'')
    def do_form(self):
        html = ('<p>self.req.method: %r</p>\n'
                '<p>self.req.query: %s</p>\n'
                '<form method="POST" action="/public/form">\n'
                '  Name:<br>\n'
                '  <input text="text" name="name"><br>\n'
                '  Comment:<br>\n'
                '  <textarea name="comment"></textarea><br>\n'
                '  <input type="submit">\n'
                '</form>\n')
        r = self.req
        return html % (r.method, h(repr(r.query)))

    @on('POST', r'')
    def do_post(self):
        html = ('<p>self.req.method: %r</p>\n'
                '<p>self.req.query: %s</p>\n'
                '<p>self.req.form: %s</p>\n'
                '<p><a href="/public/form">back</p>\n')
        r = self.req
        return html % (r.method, h(repr(r.query)), h(repr(r.form)))


mapping_list = [
    ['/public', [
        ('/hello'    , HelloAction),
        ('/environ'  , EnvironAction),
        ('/form'     , FormAction),
    ]],
]


class ActionMapping(object):

    def __init__(self, mapping_list):
        self._fixed_dict    = {}
        self._variable_list = []
        for t in self._build(mapping_list, []):
            full_urlpath, klass, funcs, rexp, prefix = t
            if prefix is None:
                self._fixed_dict[full_urlpath] = (klass, funcs)
            else:
                self._variable_list.append(t)

    def _build(self, mapping_list, new_list, base_urlpath=""):
        for urlpath, target in mapping_list:
            current_urlpath = base_urlpath + urlpath
            if isinstance(target, list):
                child_list = target
                self._build(child_list, new_list, current_urlpath)
            else:
                klass = target
                self._validate_action_class(klass)
                for upath, funcs in getattr(klass, '__mapping__'):
                    full_urlpath = current_urlpath + upath
                    rexp = re.compile(self._convert_urlpath(full_urlpath))
                    i = full_urlpath.find('{')
                    prefix = (full_urlpath[:i] if i >= 0 else None)
                    #
                    t = (full_urlpath, klass, funcs, rexp, prefix)
                    new_list.append(t)
        return new_list

    def _validate_action_class(self, klass):
        if not isinstance(klass, type):
            raise TypeError("%r: expected action class." % (klass,))
        if not issubclass(klass, BaseAction):
            raise TypeError("%r: should be a subclass of BaseAction." % klass)
        if not hasattr(klass, '__mapping__'):
            raise ValueError("%r: no mapping data." % klass)

    def _convert_urlpath(self, urlpath):   # ex: '/api/foo/{id}.json'
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
                ptype = 'str'
            if ptype not in param_rexps:
                raise ValueError("%r: contains unknown data type %r." \
                                     % (urlpath, ptype))
            if not prexp:
                prexp = param_rexps[ptype]
            #
            add(_re_escape(string))
            add('(?P<%s>%s)' % (pname, prexp))  # ex: '(?P<id>[^/]+)'
        remained = urlpath[pos:]  # ex: '.json'
        add(_re_escape(remained))
        add('$')
        return "".join(buf)   # ex: '^/api/foo/(?P<id>[^/]+)\\.json$'

    def lookup(self, req_path):
        t = self._fixed_dict.get(req_path)
        if t:
            klass, funcs = t
            kwargs = {}
            return klass, funcs, kwargs
        for _, klass, funcs, rexp, prefix in self._variable_list:
            if not req_path.startswith(prefix):
                continue
            m = rexp.match(req_path)
            if m:
                kwargs = m.groupdict()  # ex: {"id": 123}
                # ex: return FooAction, {"GET": do_show}, {"id": 123}
                return klass, funcs, kwargs
        return None, None, None


class WSGIApplication(object):

    def __init__(self, mapping_list):
        if isinstance(mapping_list, ActionMapping):
            self._mapping = mapping_list
        else:
            self._mapping = ActionMapping(mapping_list)

    def lookup(self, req_path):
        return self._mapping.lookup(req_path)

    def __call__(self, environ, start_response):
        req  = Request(environ)
        resp = Response()
        #
        req_meth = req.method
        req_path = req.path
        klass, funcs, kwargs = self.lookup(req_path)
        #
        if klass is None:
            status  = "404 Not Found"
            content = "<h2>%s</h2>" % status
        elif req_meth not in funcs:
            status  = "405 Method Not Allowed"
            content = "<h2>%s</h2>" % status
        else:
            func    = funcs[req_meth]
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
