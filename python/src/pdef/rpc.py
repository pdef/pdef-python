# encoding: utf-8
from __future__ import absolute_import
import types
import sys

import requests
from pdefc.lang import TypeEnum

import pdef
import pdef.descriptors
from pdef.invoke import Invocation


try:
    # Python 2.7
    import httplib as http_codes
except ImportError:
    # Python 3
    import http.client as http_codes

GET = 'GET'
POST = 'POST'
UTF8 = 'utf-8'
APPLICATION_JSON_CONTENT_TYPE = 'application/json; charset=utf-8'
FORM_URLENCODED_MIME_TYPE = 'application/x-www-form-urlencoded'
TEXT_PLAIN_CONTENT_TYPE = 'text/plain; charset=utf-8'


def rpc_client(interface, url, session=None):
    '''Create an RPC client.'''
    return RpcClient(interface, url, session=session)


def rpc_handler(interface, service):
    '''Create an RPC handler.'''
    return RpcHandler(interface, service)


def wsgi_app(handler):
    '''Create a WSGI RPC server.'''
    return WsgiRpcApp(handler)


class RpcException(Exception):
    def __init__(self, status, message=None):
        super(RpcException, self).__init__(message)
        self.message = message
        self.status = status


class RpcRequest(object):
    def __init__(self, method=GET, path='', query=None, post=None):
        self.method = method
        self.path = path
        self.query = dict(query) if query else {}
        self.post = dict(post) if post else {}

    def __str__(self):
        return '%s %s' % (self.method, self.path)

    def __repr__(self):
        return '<RpcRequest %s %s>' % (self.method, self.path)

    @property
    def is_post(self):
        return self.method == POST


class RpcProtocol(object):
    def __init__(self, jsonformat=None):
        self.jsonformat = jsonformat or pdef.jsonformat

    def get_request(self, invocation):
        if not invocation:
            raise ValueError('Invocation required')

        method = invocation.method
        if not method.is_terminal:
            raise ValueError('Last invocation method must be terminal')

        request = RpcRequest()
        request.method = POST if method.is_post else GET
        for inv in invocation.to_chain():
            self._write_invocation(request, inv)

        return request

    def _write_invocation(self, request, invocation):
        method = invocation.method
        kwargs = invocation.kwargs

        post = request.post
        query = request.query
        path = '/' + method.name

        for argd in method.args:
            name = argd.name
            kwarg = kwargs.get(name)
            if kwarg is None:
                if argd.is_post or argd.is_query:
                    continue
                raise ValueError('Interface method argument "%s" cannot be null' % name)

            value = self._to_json(kwarg, argd.type)
            if method.is_interface:
                path += '/' + urlencode(value)
            elif method.is_post:
                post[name] = value
            else:
                query[name] = value

        request.path += path

    def _to_json(self, kwarg, descriptor):
        '''Serialize a kwarg to json, strip quotes.'''
        s = self.jsonformat.write(kwarg, descriptor)
        return s.strip('"')

    def get_invocation(self, request, interface_descriptor):
        '''Parse an invocation from an rpc request using an interface descriptor.'''
        if not request:
            raise ValueError('Request required')
        if not interface_descriptor:
            raise ValueError('Interface descriptor required')

        invocation = None
        parts = request.path.strip('/').split('/')

        while parts:
            part = parts.pop(0)

            # Find a method by a name.
            method = interface_descriptor.find_method(part)
            if not method:
                raise RpcException(http_codes.BAD_REQUEST, 'Method not found')

            # Check the required HTTP method.
            if method.is_post and not request.is_post:
                raise RpcException(http_codes.METHOD_NOT_ALLOWED,
                                   'Method not allowed, POST required')

            # Parse keyword arguments.
            kwargs = self._read_kwargs(method, parts, request.query, request.post)

            # Create a root invocation,
            # or a next invocation in a chain.
            invocation = invocation.next(method, **kwargs) \
                if invocation else Invocation(method, kwargs=kwargs)

            if method.is_terminal:
                break

            # It's an interface method.
            # Get the next interface descriptor and proceed parsing the parts.
            interface_descriptor = method.result

        if parts:
            # No more interface descriptors in a chain, but the parts are still present.
            raise RpcException(http_codes.BAD_REQUEST, 'Failed to parse an invocation chain')

        if not invocation:
            raise RpcException(http_codes.BAD_REQUEST, 'Methods required')

        if not invocation.method.is_terminal:
            raise RpcException(http_codes.BAD_REQUEST, 'The last method must be a terminal one. '
                                                       'It must return a data type or be void.')

        return invocation

    def _read_kwargs(self, method, parts, query, post):
        kwargs = {}

        for argd in method.args:
            name = argd.name

            if method.is_interface:
                if not parts:
                    raise RpcException(http_codes.NOT_FOUND, 'Wrong number of method args: "%s"'
                                                             % method.name)
                value = urldecode(parts.pop(0))
            elif method.is_post:
                value = post.get(name)
            else:
                value = query.get(name)

            if value is None:
                kwargs[name] = None
            else:
                kwargs[name] = self._from_json(value, argd.type)

        return kwargs

    def _from_json(self, s, descriptor):
        if s is None:
            return None

        type0 = descriptor.type
        if type0 in (TypeEnum.STRING, TypeEnum.DATETIME, TypeEnum.ENUM):
            if not (s.startswith('"') and s.endswith('"')):
                # Return the quotes to get a valid json string.
                s = '"' + s + '"'

        return self.jsonformat.read(s, descriptor)


class RpcClient(object):
    def __init__(self, interface, url, session=None, protocol=None):
        if not interface:
            raise ValueError('Interface required')
        if not url:
            raise ValueError('Url required')

        self.interface = interface
        self.interface_descriptor = interface.descriptor

        self.url = url
        self.session = session or requests.session()
        self.protocol = protocol or RpcProtocol()

    def proxy(self):
        return pdef.proxy(self.interface, self)

    def __call__(self, invocation):
        if not invocation:
            raise ValueError('Invocation required')

        rpc_request = self.protocol.get_request(invocation)

        method = invocation.method
        resultd = method.result
        excd = self.interface_descriptor.exc

        request = self._build_request(rpc_request)
        return self._send(request, resultd, excd)

    def _build_request(self, rpc_request):
        url = self._build_url(rpc_request.path)
        return requests.Request(method=rpc_request.method,
                                url=url,
                                data=rpc_request.post,
                                params=rpc_request.query)

    def _build_url(self, path):
        return self.url + path

    def _send(self, request, resultd, excd=None):
        session = self.session
        prepared = request.prepare()
        response = session.send(prepared)
        return self._parse_response(response, resultd, excd)

    def _parse_response(self, response, resultd, excd=None):
        code = response.status_code

        if code not in (http_codes.OK, http_codes.UNPROCESSABLE_ENTITY):
            # It's an HTTP error.
            return self._parse_error(response)

        # It's a successful rpc result.
        text = response.text

        # Create a generic rpc result class.
        result_class = rpc_result_class(resultd, excd)
        result = result_class.from_json(text)

        if code == http_codes.OK:
            return result.data
        else:
            exc = result.error or RpcException(code, 'Unsupported application exception')
            raise exc

    def _parse_error(self, response):
        try:
            text = response.text
        except Exception as e:
            text = 'Failed to get the response text, e=%s' % e

        # Limit the text to use in as an exception description.
        text = text if len(text) < 255 else text[:255]
        raise RpcException(response.status_code, text)


class RpcHandler(object):
    def __init__(self, interface, service, protocol=None):
        if not interface:
            raise ValueError('Interface required')
        if not service:
            raise ValueError('Service required')
        self.interface = interface
        self.interface_descriptor = interface.descriptor
        self.service = service
        self.protocol = protocol or RpcProtocol()

    def __call__(self, rpc_request):
        return self.handle(rpc_request)

    def handle(self, rpc_request):
        '''Handle an rpc request and return a tuple (is_successful, rpc_result).'''
        if not rpc_request:
            raise ValueError('Rpc request required')

        invocation = self.protocol.get_invocation(rpc_request, self.interface_descriptor)

        method = invocation.method
        datad = method.result
        excd = self.interface_descriptor.exc
        result_class = rpc_result_class(datad, excd)

        try:
            data = invocation.invoke(self.service)
            return True, result_class(data)
        except Exception as e:
            if excd and isinstance(e, excd.pyclass):
                # It's an expected application exception.
                return False, result_class(data=None, error=e)

            # Not an application exception, reraise it.
            raise


class WsgiRpcApp(object):
    '''WSGI RPC application.'''

    def __init__(self, handler):
        if not handler:
            raise ValueError('Handler required')
        self.handler = handler

    def __call__(self, environ, start_response):
        return self.handle(environ, start_response)

    def handle(self, environ, start_response):
        request = self._parse_request(environ)
        try:
            success, result = self.handler(request)
        except RpcException as e:
            status = e.status or http_codes.INTERNAL_SERVER_ERROR
            content = e.message or 'Internal server error'
            return self._response(start_response, status, content)

        status_code = http_codes.OK if success else http_codes.UNPROCESSABLE_ENTITY
        content = result.to_json(indent=True)
        return self._response(start_response, status_code, content,
                              content_type=APPLICATION_JSON_CONTENT_TYPE)

    def _parse_request(self, env):
        '''Create an http server request from a wsgi request.'''
        method = env['REQUEST_METHOD']
        path = env['PATH_INFO']
        query = self._read_wsgi_query(env)
        post = self._read_wsgi_post(env)

        return RpcRequest(method, path=path, query=query, post=post)

    def _read_wsgi_query(self, env):
        if 'QUERY_STRING' not in env:
            return {}
        s = env['QUERY_STRING']
        return self._parse_query(s)

    def _read_wsgi_post(self, env):
        ctype = env.get('CONTENT_TYPE', '')
        clength = self._read_wsgi_clength(env)

        body = None
        if clength > 0 and ctype.lower().startswith(FORM_URLENCODED_MIME_TYPE):
            body = env['wsgi.input'].read(clength)

        if not body:
            return {}

        if sys.version > '3':
            body = body.decode(UTF8)

        return self._parse_query(body)

    def _read_wsgi_clength(self, env):
        clength = env.get('CONTENT_LENGTH') or 0
        try:
            return int(clength)
        except (ValueError, TypeError):
            return 0

    def _parse_query(self, s):
        d = parse_query(s)
        result = {}
        for key, values in d.items():
            result[key] = values[0] if values else ''
        return result

    def _response(self, start_response, status_code, unicode_content, content_type=None):
        reason = http_codes.responses.get(status_code)
        status = '%s %s' % (status_code, reason)

        content = unicode_content.encode(UTF8)
        content_type = content_type or TEXT_PLAIN_CONTENT_TYPE
        headers = [('Content-Type', content_type),
                   ('Content-Length', str(len(content)))]

        start_response(status, headers)
        return [content]


def rpc_result_class(datad, excd=None):
    '''Create a generic RpcResult class with a given data and exception descriptors.'''

    class RpcResult(pdef.Message):
        data = pdef.descriptors.field('data', datad)
        error = pdef.descriptors.field('error', excd or pdef.descriptors.string0)
        descriptor = pdef.descriptors.message(lambda: RpcResult, fields=[data, error])

        has_data = data.has_property
        has_error = error.has_property

        def __init__(self, data=None, error=None):
            self.data = data
            self.error = error

    return RpcResult


try:
    # Python 2.7
    import urllib
    import urlparse

    def urlencode(s, safe='[]{},.-"'):
        if isinstance(s, types.UnicodeType):
            s = s.encode(UTF8)

        if isinstance(safe, types.UnicodeType):
            safe = safe.encode(UTF8)

        result = urllib.quote_plus(s, safe)
        return result.decode(UTF8)

    def urldecode(s):
        if isinstance(s, types.UnicodeType):
            s = s.encode(UTF8)

        result = urllib.unquote_plus(s)
        return result.decode(UTF8)

    def parse_query(s):
        if isinstance(s, types.UnicodeType):
            s = s.encode(UTF8)

        q = urlparse.parse_qs(s)

        # Decode the result to unicode.
        result = {}
        for key, values in q.items():
            k = key.decode(UTF8)
            vv = [v.decode(UTF8) for v in values] if values else []
            result[k] = vv

        return result

except ImportError:
    # Python 3
    import urllib.parse

    def urlencode(s, safe='[]{},.-"'):
        return urllib.parse.quote_plus(s, safe, encoding=UTF8)

    def urldecode(s):
        return urllib.parse.unquote_plus(s, encoding=UTF8)

    def parse_query(s):
        return urllib.parse.parse_qs(s)
