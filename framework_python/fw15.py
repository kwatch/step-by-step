# -*- coding: utf-8 -*-

##
## subject: ActionクラスにURLパスパターンと関数のマッピングを定義
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


class HelloAction(Action):

    ITEMS = [
        {"name": "Alice"},
        {"name": "Bob"},
        {"name": "Charlie"},
    ]

    def do_index(self):
        return {
            "items": self.ITEMS,
        }

    def do_show(self, name):
        for x in self.ITEMS:
            if x['name'] == name:
                break
        else:
            self.resp.status = "404 Not Found"
            return {"error": "404 Not Found"}
        msg = "Hello, %s!" % name
        return {"message": msg}

    __mapping__ = [
        (r'.json',              {'GET': do_index}),
        (r'/{name:<\w+>}.json', {'GET': do_show}),
    ]


class EnvironAction(Action):

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

    __mapping__ = [
        (r'',             {'GET': do_render}),
    ]


class FormAction(Action):

    def do_form(self):
        req_meth = self.req.method
        html = ('<p>REQUEST_METHOD: %r</p>\n'
                '<form method="POST" action="/public/form">\n'
                '<input type="submit">\n'
                '</form>\n')
        return html % req_meth

    def do_post(self):
        req_meth = self.req.method
        html = ('<p>REQUEST_METHOD: %r</p>\n'
                '<p><a href="/public/form">back</p>\n')
        return html % req_meth

    __mapping__ = [
        (r'',   {'GET': do_form, 'POST': do_post}),
    ]


mapping_list = [
    ['/public', [
        ('/hello'    , HelloAction),
        ('/environ'  , EnvironAction),
        ('/form'     , FormAction),
    ]],
]


class ActionMapping(object):

    def __init__(self, mapping_list):
        self._mapping_list = self._build(mapping_list, [])

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
                    t = (full_urlpath, rexp, klass, funcs)
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
        for _, rexp, klass, funcs in self._mapping_list:
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
