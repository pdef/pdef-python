# encoding: utf-8
import copy
from datetime import datetime
import httplib
import unittest
import urllib
from mock import Mock
from StringIO import StringIO
from threading import Thread

import pdef
from pdef import descriptors
from pdef.rpc import *
from pdef_test.messages import TestMessage
from pdef_test.interfaces import TestInterface, TestException


class TestRpcProtocol(unittest.TestCase):
    def setUp(self):
        handler = lambda inv: inv
        self.proxy = pdef.proxy(TestInterface, handler)
        self.protocol = RpcProtocol()

    # get_request.

    def test_get_request(self):
        invocation = self.proxy.method(1, 2)
        request = self.protocol.get_request(invocation)

        assert request.method == GET
        assert request.path == '/method/1/2'
        assert request.query == {}
        assert request.post == {}

    def test_get_request(self):
        invocation = self.proxy.query(1, 2)
        request = self.protocol.get_request(invocation)

        assert request.method == GET
        assert request.path == '/query'
        assert request.query == {'arg0': '1', 'arg1': '2'}
        assert request.post == {}

    def test_get_request__post(self):
        invocation = self.proxy.post(1, 2)
        request = self.protocol.get_request(invocation)

        assert request.method == POST
        assert request.path == '/post'
        assert request.query == {}
        assert request.post == {'arg0': '1', 'arg1': '2'}

    def test_get_request__chained_methods(self):
        invocation = self.proxy.interface0(1, 2).method(3, 4)
        request = self.protocol.get_request(invocation)

        assert request.method == GET
        assert request.path == '/interface0/1/2/method/3/4'
        assert request.query == {}
        assert request.post == {}

    def test_get_request__urlencode_path_args(self):
        invocation = self.proxy.string0(u'Привет')
        request = self.protocol.get_request(invocation)

        assert request.path == '/string0/%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82'

    # to_json.

    def test_to_json__no_quotes(self):
        result = self.protocol._to_json(u'Привет," мир!', descriptors.string0)

        assert result == u'Привет,\\\" мир!'

    # get_invocation.

    def test_get_invocation(self):
        request = RpcRequest(path='/method/1/2/')

        invocation = self.protocol.get_invocation(request, TestInterface.descriptor)
        assert invocation.method.name == 'method'
        assert invocation.kwargs == {'arg0': 1, 'arg1': 2}

    def test_get_invocation__query_method(self):
        request = RpcRequest(path='/query', query={'arg0': '1', 'arg1': '2'})

        invocation = self.protocol.get_invocation(request, TestInterface.descriptor)
        assert invocation.method.name == 'query'
        assert invocation.kwargs == {'arg0': 1, 'arg1': 2}

    def test_get_invocation__post_method(self):
        request = RpcRequest(POST, path='/post', post={'arg0': '1', 'arg1': '2'},)

        invocation = self.protocol.get_invocation(request, TestInterface.descriptor)
        assert invocation.method.name == 'post'
        assert invocation.kwargs == {'arg0': 1, 'arg1': 2}

    def test_get_invocation__post_method_not_allowed(self):
        request = RpcRequest(GET, path='/post', post={})
        try:
            self.protocol.get_invocation(request, TestInterface.descriptor)
            self.fail()
        except RpcException as e:
            assert e.status == httplib.METHOD_NOT_ALLOWED

    def test_get_invocation__chained_method_index(self):
        request = RpcRequest(path='/interface0/1/2/query', query={'arg0': '3'})

        chain = self.protocol.get_invocation(request, TestInterface.descriptor).to_chain()
        invocation0 = chain[0]
        invocation1 = chain[1]

        assert len(chain) == 2
        assert invocation0.method.name == 'interface0'
        assert invocation0.kwargs == {'arg0': 1, 'arg1': 2}
        assert invocation1.method.name == 'query'
        assert invocation1.kwargs == {'arg0': 3, 'arg1': None}

    def test_get_invocation__last_method_not_terminal(self):
        request = RpcRequest(path='/interface0/1/2')

        try:
            self.protocol.get_invocation(request, TestInterface.descriptor)
            self.fail()
        except RpcException as e:
            assert e.status == httplib.NOT_FOUND

    def test_get_invocation__urldecode_path_args(self):
        request = RpcRequest(path='/string0/%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82')

        invocation = self.protocol.get_invocation(request, TestInterface.descriptor)
        assert invocation.method.name == 'string0'
        assert invocation.kwargs == {'text': u'Привет'}

    # from_json.

    def test_from_json(self):
        message = TestMessage(string0=u'Привет', bool0=True, int0=123)
        json = message.to_json()
        result = self.protocol._from_json(json, TestMessage.descriptor)

        assert result == message

    def test_from_json__unquoted_string(self):
        result = self.protocol._from_json(u'Привет', descriptors.string0)
        assert result == u'Привет'


class TestRpcClient(unittest.TestCase):
    def setUp(self):
        self.session = Mock()
        self.client = rpc_client(TestInterface, 'http://localhost:8080', session=self.session)

    def test_build_request(self):
        rpc_req = RpcRequest(POST, path='/method/1/2', query={'key': 'value'},
                             post={'key': 'value'})
        req = self.client._build_request(rpc_req)

        assert req.method == POST
        assert req.url == 'http://localhost:8080/method/1/2'
        assert req.data == {'key': 'value'}
        assert req.params == {'key': 'value'}

    def test_parse_response__ok(self):
        response = requests.Response()
        response.status_code = httplib.OK
        response._content = '123'

        result = self.client._parse_response(response, descriptors.int32)
        assert result == 123

    def test_parse_response__application_exc(self):
        exc = TestException('Test exception')
        response = requests.Response()
        response.status_code = httplib.UNPROCESSABLE_ENTITY
        response._content = exc.to_json().encode('utf-8')

        try:
            self.client._parse_response(response, descriptors.int32, TestException.descriptor)
            self.fail()
        except TestException as e:
            assert e == exc

    def test_parse_response__server_error(self):
        response = requests.Response()
        response.status_code = httplib.NOT_FOUND
        response._content = 'Method not found'.encode('utf-8')

        try:
            self.client._parse_response(response, None, None)
            self.fail()
        except RpcException as e:
            assert e.status == httplib.NOT_FOUND
            assert e.message == 'Method not found'


class TestRpcHandler(unittest.TestCase):
    def setUp(self):
        self.service = Mock()
        self.handler = RpcHandler(TestInterface, self.service)

    def test_handle__rpc_exception(self):
        try:
            request = RpcRequest(path='/wrong/method')
            self.handler(request)
            self.fail()
        except RpcException as e:
            assert e.status == httplib.NOT_FOUND

    def test_handle__ok(self):
        self.service.method = Mock(return_value=3)
        request = RpcRequest(path='/method/1/2')

        success, data, datad = self.handler(request)
        assert success is True
        assert data == 3
        assert datad is descriptors.int32

    def test_handle__application_exception(self):
        e = TestException(text='Hello, world')
        self.service.method = Mock(side_effect=e)
        request = RpcRequest(path='/method/1/2')

        success, value, valued = self.handler(request)
        assert success is False
        assert value == e
        assert valued is TestException.descriptor

    def test_handle__unexpected_exception(self):
        self.service.method = Mock(side_effect=ValueError)
        request = RpcRequest(path='/method/1/2')
        try:
            self.handler(request)
            self.fail()
        except ValueError:
            pass


class TestWsgiRpcServer(unittest.TestCase):
    def env(self):
        return {
            'REQUEST_METHOD': 'GET',
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'CONTENT_LENGTH': 0,
            'SCRIPT_NAME': '/myapp',
            'PATH_INFO': '/method0/method1'
        }

    def test_handle(self):
        hello = u'Привет, мир'
        handler = lambda request: (True, hello, descriptors.string0)

        server = wsgi_server(handler)
        start_response = Mock()
        content = ''.join(server(self.env(), start_response))

        assert content.decode(UTF8) == '"' + hello + '"'
        start_response.assert_called_with('200 OK',
            [('Content-Type', 'application/json; charset=utf-8'),
             ('Content-Length', '%s' % len(content))])

    def test_handle__rpc_exc(self):
        def handler(request):
            raise RpcException(httplib.NOT_FOUND, 'Method not found')

        server = wsgi_server(handler)
        start_response = Mock()
        content = ''.join(server(self.env(), start_response))

        assert content.decode(UTF8) == 'Method not found'
        start_response.assert_called_with('404 Not Found',
            [('Content-Type', 'text/plain; charset=utf-8'),
             ('Content-Length', '%s' % len(content))])

    def test_get_invocation(self):
        query = urllib.quote(u'привет=мир'.encode('utf-8'), '=')
        body = urllib.quote(u'пока=мир'.encode('utf-8'), '=')
        env = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'CONTENT_LENGTH': len(body),
            'SCRIPT_NAME': '/myapp',
            'PATH_INFO': '/method0/method1',
            'QUERY_STRING': query,
            'wsgi.input': StringIO(body),
        }

        server = WsgiRpcServer(Mock())
        request = server._parse_request(env)

        assert request.method == 'POST'
        assert request.path == '/method0/method1'
        assert request.query == {u'привет': u'мир'}
        assert request.post == {u'пока': u'мир'}


class TestIntegration(unittest.TestCase):
    def setUp(self):
        from wsgiref.simple_server import make_server
        self.service = Mock()

        handler = rpc_handler(TestInterface, self.service)
        app = wsgi_server(handler)

        self.server = make_server('localhost', 0, app)
        self.server_thread = Thread(target=self.server.serve_forever)
        self.server_thread.start()

        url = 'http://localhost:%s/' % self.server.server_port
        self.client = rpc_client(TestInterface, url).proxy()

        import logging
        FORMAT = '%(name)s %(levelname)s - %(message)s'
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)

    def tearDown(self):
        self.server.shutdown()

    def test(self):
        client = self.client
        service = self.service
        message = TestMessage(u'Привет', True, -123)
        exc = TestException('Test exception')
        dt = datetime(2013, 11, 17, 19, 41)

        service.method = Mock(return_value=3)
        service.query = Mock(return_value=7)
        service.post = Mock(return_value=11)
        service.string0 = Mock(return_value=u'Пока')
        service.datetime0 = Mock(return_value=dt)
        service.message0 = Mock(return_value=copy.deepcopy(message))
        service.interface0 = Mock(return_value=service)

        service.void0 = Mock(return_value=None)
        service.exc0 = Mock(side_effect=copy.deepcopy(exc))
        service.serverError = Mock(side_effect=ValueError('Test exception'))

        assert client.method(1, 2) == 3
        service.method.assert_called_with(arg0=1, arg1=2)

        assert client.query(3, 4) == 7
        service.query.assert_called_with(arg0=3, arg1=4)

        assert client.post(5, 6) == 11
        service.post.assert_called_with(arg0=5, arg1=6)

        assert client.string0(u'Привет') == u'Пока'
        service.string0.assert_called_with(text=u'Привет')

        assert client.datetime0(dt) == dt
        service.datetime0.assert_called_with(dt=dt)

        assert client.message0(message) == message
        service.message0.assert_called_with(msg=message)

        assert client.interface0(1, 2).query(3, 4) == 7
        service.interface0.assert_called_with(arg0=1, arg1=2)

        assert client.void0() is None
        service.void0.assert_called_with()

        try:
            client.exc0()
            self.fail()
        except TestException as e:
            assert e == exc

        self.assertRaises(RpcException, client.serverError)
