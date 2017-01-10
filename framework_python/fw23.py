# -*- coding: utf-8 -*-

##
## subject: クッキーをサポート
##

import sys
import os
import re
import json
from urllib.parse import unquote_plus, quote_plus
from html import escape as h
from datetime import date, datetime, timedelta


class HttpException(Exception):

    def __init__(self, status, content=None, headers=None):
        self.status  = status
        self.content = content
        self.headers = headers


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
        return self.environ.get('CONTENT_TYPE')

    @property
    def content_length(self):
        s = self.environ.get('CONTENT_LENGTH')
        try:
            return int(s) if s else None
        except:
            msg = "<p>%r: invalid content lenght.</p>"
            raise HttpException(400, msg % (s,))

    MAX_FORM_SIZE      =   1 * 1024 * 1024  #  2MB
    MAX_JSON_SIZE      =   1 * 1024 * 1024  #  2MB
    MAX_MULTIPART_SIZE =  10 * 1024 * 1024  # 10MB

    @property
    def query(self):
        if not hasattr(self, '_query'):
            self._query = _parse_query_str(self.query_string)
        return self._query

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._check_ctype("application/x-www-form-urlencoded")
            self._form = _parse_query_str(self._read_input(self.MAX_FORM_SIZE))
        return self._form

    @property
    def json(self):
        if not hasattr(self, '_json'):
            self._check_ctype("application/json")
            self._json = json.loads(self._read_input(self.MAX_JSON_SIZE))
        return self._json

    @property
    def multipart(self):
        if not hasattr(self, '_multipart'):
            self._check_ctype("multipart/form-data")
            mp = MultiPart(self.content_type)
            strs, files = mp.parse(self._read_input(self.MAX_MULTIPART_SIZE))
            self._multipart = (strs, files)
        return self._multipart

    def _read_input(self, max_size):
        if hasattr(self, '_eof'):
            return ""
        if self.content_length is None:
            raise _http400("content-length required.")
        if self.content_length > max_size:
            raise _http400("content-length too large.")
        input   = self.environ['wsgi.input']
        binary  = input.read(self.content_length)
        self._eof = True
        unicode = binary.decode('utf-8')
        return unicode

    def _check_ctype(self, expected):
        ctype = self.content_type or ""
        if not ctype.startswith(expected):
            msg = "expected content type is %r, but actual is %r."
            raise _http400(msg % (expected, ctype))

    @property
    def cookies(self):
        if not hasattr(self, '_cookies'):
            cookie_str = self.environ.get('HTTP_COOKIE')
            self._cookies = _parse_cookie_str(cookie_str)
        return self._cookies


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


def _parse_cookie_str(cookie_str):
    d = {}
    if cookie_str:
        unq = unquote_plus
        for s in cookie_str.split(';'):   # ex: 'x=1; y=2' -> ['x=1', ' y=2']
            kv = s.strip().split('=', 1)  # ex: ' x=1' -> ['x', '1']; 'x' -> ['x']
            k, v = kv if len(kv) == 2 else (kv[0], "")
            d[unq(k)] = unq(v)
    return d


def _http400(msg):
    status = "400 Bad Request"
    content = "%s: %s" % (status, msg)
    return HttpException(status, content)


class MultiPart(object):

    def __init__(self, content_type):
        if not content_type:
            raise _http400("content type required.")
        if not content_type.startswith("multipart/form-data;"):
            raise _http400("not a multipart.")
        m = re.search(r'''boundary=(['"]?)([-\w]+)\1?''', content_type)
        if not m:
            raise _http400("boundary required.")
        self.boundary = m.group(2)

    def parse(self, string):
        strs  = {}
        files = {}
        for t in self._each_entry(string):
            name, val, filename = t
            if not name:
                continue
            d = files if filename else strs
            if filename:
                v = (val, filename)
                d = files
            else:
                v = val
                d = strs
            if name.endswith('[]'):
                d.setdefault(name, []).append(v)
            else:
                d[name] = v
        return strs, files

    def _each_entry(self, string):
        boundary  = self.boundary
        separator = "\r\n--%s\r\n"   % boundary
        preamble  =     "--%s\r\n"   % boundary
        postamble = "\r\n--%s--\r\n" % boundary
        arr = string.split(separator)
        if not arr[0].startswith(preamble):
            raise _http400("preamble unmatched.")
        if not arr[-1].endswith(postamble):
            raise _http400("postamble unmatched.")
        arr[0]  = arr[0][len(preamble):]
        arr[-1] = arr[-1][:-len(postamble)]
        #
        pat  = r'^Content-Disposition: *form-data(?:; *name="(.*?)")?(?:; *filename="(.*?)")?'
        rexp = re.compile(pat, re.M | re.I)
        for s in arr:
            pair = s.split("\r\n\r\n", 1)
            if len(pair) != 2:
                raise _http400("missing header part.")
            header, val = pair
            m = rexp.search(header)
            if not m:
                raise _http400("invalid content disposition.")
            name, filename = m.groups()
            name     = unquote_plus(name)     if name else None
            filename = unquote_plus(filename) if filename else None
            val      = unquote_plus(val)
            yield name, val, filename


class Response(object):

    def __init__(self):
        self.status  = "200 OK"
        self.headers = {
            'Content-Type': "text/html;charset=utf-8",
        }
        self._cookies = []

    def header_list(self):
        items = list(self.headers.items())
        if self._cookies:
            k = 'Set-Cooie'
            items.extend( (k, s) for s in self._cookies )
        return items

    @property
    def content_type(self):
        return self.headers['Content-Type']

    @content_type.setter
    def content_type(self, value):
        self.headers['Content-Type'] = value

    ## クッキーを追加する。名前と値は必須、それ以外は省略可。
    def add_cookie(self, name, value,
                   domain=None, path=None, expires=None, max_age=None,
                   httponly=None, secure=None):
        ## expiresには、文字列かdate型を指定する。
        ## なおPythonではUTCへの変換が面倒なため、datetime型はエラー
        if expires is None:
            pass
        elif isinstance(expires, date):
            expires = http_datetime(expires)
        elif isinstance(expires, datetime):
            raise TypeError("'expires' should be date, not datetime."
                            " Use 'max_age' keyword arg instead.")
        #
        buf = []; add = buf.append
        add("%s=%s" % (quote_plus(name), quote_plus(value)))
        if domain  : add("; Domain=%s"  % domain)
        if path    : add("; Path=%s"    % path)
        if expires : add("; Expires=%s" % expires)
        if max_age : add("; Max-Age=%s" % max_age)
        if httponly: add("; HttpOnly")
        if secure  : add("; Secure")
        cookie_str = "".join(buf)
        self._cookies.append(cookie_str)
        return cookie_str

    ## 過去の遠い日付をexpiresに設定することで、クッキーを無効化する
    def expire_cookie(self, cookie_name,
                      domain=None, path=None, max_age=None,
                      httponly=None, secure=None):
        expires = 'Thu, 01 Jan 1970 00:00:00 GMT'  # past date
        self.add_cookie(cookie_name, "",
                        domain=domain, path=path, expires=expires, max_age=max_age,
                        httponly=httponly, secure=secure)


def http_datetime(dt):
    ## strftime()は、ロケールによっては月名や曜日名が英語にならないことがある
    #return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')
    ## かわりに、月名と曜日名を自前で設定する
    w    = dt.weekday()  # Mon: 0, Tue: 1, ...., Sat: 5, Sun: 6
    wday = _WEEKDAYS[w]
    mon  = _MONTHS[dt.month]
    ## なおHTTPでの日時はGMTを使うので、必ずUTCのdatetimeを使うこと
    fmt  = "{}, %d {} %Y %H:%M:%S GMT"
    ## ex: 'Sat, 01 Jan 2000 12:34:56 GMT'
    return dt.strftime(fmt).format(wday, mon)

_WEEKDAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
_MONTHS   = (None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


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
        req_meth = self.req.method
        html = ('<p>self.req.method: %r</p>\n'
                '<p>self.req.query: %s</p>\n'
                '<form method="POST" action="/public/form"\n'
                '      enctype="multipart/form-data">\n'
                '  Name:<br>\n'
                '  <input type="text" name="name"><br>\n'
                '  Comment:<br>\n'
                '  <textarea name="comment"></textarea><br>\n'
                '  File:<br>\n'
                '  <input type="file" name="upfile"><br>\n'
                '  <input type="submit">\n'
                '</form>\n')
        r = self.req
        return html % (r.method, h(repr(r.query)))

    @on('POST', r'')
    def do_post(self):
        pair = self.req.multipart
        html = ('<p>self.req.method: %r</p>\n'
                '<p>self.req.query: %s</p>\n'
                '<p>self.req.multipart: %s</p>\n'
                '<p><a href="/public/form">back</p>\n')
        r = self.req
        return html % (r.method, h(repr(r.query)), h(repr(r.multipart)))


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

    def __init__(self, mapping_list, auto_redirect=True):
        if isinstance(mapping_list, ActionMapping):
            self._mapping = mapping_list
        else:
            self._mapping = ActionMapping(mapping_list)
        self._auto_redirect = auto_redirect

    def lookup(self, req_path):
        return self._mapping.lookup(req_path)

    def __call__(self, environ, start_response):
        try:
            status, header_list, content = self._handle_request(environ)
        except HttpException as ex:
            status, header_list, content = self._handle_http_exception(ex)
        body = [content.encode('utf-8')]
        start_response(status, header_list)
        return body

    def _handle_request(self, environ):
        req  = Request(environ)
        resp = Response()
        #
        req_meth = req.method
        req_path = req.path
        klass, funcs, kwargs = self.lookup(req_path)
        #
        if klass is None:
            self._try_auto_redirect(req)
            raise HttpException("404 Not Found")
        if req_meth not in funcs:
            raise HttpException("405 Method Not Allowed")
        #
        func    = funcs[req_meth]
        action  = klass(req, resp)
        content = action.handle_action(func, kwargs)
        status  = resp.status
        if req_meth == 'HEAD':
            content = ""
        #
        header_list = resp.header_list()  # ex: [('Content-Type': 'text/html')]
        return status, header_list, content

    def _handle_http_exception(self, ex):
        content = ex.content or "<h2>%s</h2>" % ex.status
        headers = {"Content-Type": "text/html;charset=utf-8"}
        if ex.headers:
            headers.update(ex.headers)
        header_list = list(headers.items())  # ex: {'X': 'Y'} -> [('X', 'Y')]
        return ex.status, header_list, content

    def _try_auto_redirect(self, req):
        if not self._auto_redirect:
            return
        if not req.method in ('GET', 'HEAD'):
            return
        s = req.path
        rpath = (s[:-1] if s.endswith('/') else s+'/')
        klass, _, _ = self.lookup(rpath)
        if klass is None:
            return
        qs = req.query_string
        location = "%s?%s" % (rpath, qs) if qs else rpath
        raise HttpException("301 Moved Permanently", location,
                            {'Location': location})


wsgi_app = WSGIApplication(mapping_list)


if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    wsgi_server = make_server('localhost', 7000, wsgi_app)
    wsgi_server.serve_forever()
