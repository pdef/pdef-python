# encoding: utf-8
import unittest
from mock import Mock

from pdef.invoke import *
from pdef import descriptors
from pdef_test.messages import TestMessage
from pdef_test.interfaces import TestInterface, TestException


class TestInvocation(unittest.TestCase):
    def test_init(self):
        method = descriptors.method('method', descriptors.void,
                                    args=(descriptors.arg('a', descriptors.int32),
                                          descriptors.arg('b', descriptors.int32)))
        invocation = Invocation(method, args=[1, 2])

        assert invocation.method is method
        assert invocation.kwargs == {'a': 1, 'b': 2}

    def test_next(self):
        method0 = descriptors.method('method0', descriptors.interface(object))
        method1 = descriptors.method('method1', descriptors.void,
                                     args=(descriptors.arg('a', descriptors.int32),
                                           descriptors.arg('b', descriptors.int32)))

        invocation0 = Invocation(method0)
        invocation1 = invocation0.next(method1, 1, 2)

        assert invocation1.parent is invocation0
        assert invocation1.method is method1
        assert invocation1.kwargs == {'a': 1, 'b': 2}

    def test_to_chain(self):
        method0 = descriptors.method('method0', descriptors.interface(object))
        method1 = descriptors.method('method1', descriptors.interface(object))
        method2 = descriptors.method('method2', descriptors.void)

        invocation0 = Invocation(method0)
        invocation1 = invocation0.next(method1)
        invocation2 = invocation1.next(method2)

        chain = invocation2.to_chain()
        assert chain == [invocation0, invocation1, invocation2]

    def test_invoke(self):
        class Service(object):
            def method(self, a=None, b=None):
                return a + b

        method = descriptors.method('method', descriptors.int32,
                                    args=(descriptors.arg('a', descriptors.int32),
                                          descriptors.arg('b', descriptors.int32)))
        invocation = Invocation(method, args=(1, 2))
        service = Service()
        assert invocation.invoke(service) == 3

    def test_invoke_exc(self):
        class Service(object):
            def method(self):
                raise TestException('Hello')

        method = descriptors.method('method', descriptors.void)
        invocation = Invocation(method)
        service = Service()

        try:
            invocation.invoke(service)
        except TestException as e:
            assert e == TestException('Hello')

    def test_invoke_kwargs_with_default_primitives(self):
        method = descriptors.method('method', descriptors.void, args=[
            descriptors.arg('arg0', descriptors.int32),
            descriptors.arg('arg1', descriptors.string0)
        ])

        interface = Mock()
        interface.method = Mock()

        invocation = Invocation(method)
        invocation.invoke(interface)

        interface.method.assert_called_once_with(arg0=0, arg1='')

    def test_build_args(self):
        method = descriptors.method('method', descriptors.void,
                                    args=(descriptors.arg('a', descriptors.int32),
                                          descriptors.arg('b', descriptors.int32)))
        build = lambda args, kwargs: Invocation._build_kwargs(method, args, kwargs)
        expected = {'a': 1, 'b': 2}

        assert build([1, 2], None) == expected
        assert build(None, {'a': 1, 'b': 2}) == expected
        assert build([1], {'b': 2}) == expected
        assert build(None, None) == {'a': None, 'b': None}

        self.assertRaises(TypeError, build, [1, 2, 3], None)
        self.assertRaises(TypeError, build, [1, 2], {'a': 1, 'b': 2})
        self.assertRaises(TypeError, build, None, {'a': 1, 'b': 2, 'c': 3})
        self.assertRaises(TypeError, build, None, {'c': 3})

    def test_deep_copy_args(self):
        method = descriptors.method('method', descriptors.void,
            args=(descriptors.arg('arg0', descriptors.list0(TestMessage.descriptor)),
                  descriptors.arg('arg1', descriptors.set0(descriptors.int32))
            ))

        list0 = [TestMessage('hello'), TestMessage('world')]
        set0 = {1, 2, 3}

        invocation = Invocation(method, args=(list0, set0))
        arg0 = invocation.kwargs['arg0']
        arg1 = invocation.kwargs['arg1']

        assert arg0 == list0
        assert arg1 == set0

        assert arg0 is not list0
        assert arg1 is not set0

        assert arg0[0] is not list0[0]
        assert arg0[1] is not list0[1]


class TestInvocationProxy(unittest.TestCase):
    def proxy(self):
        return proxy(TestInterface, lambda invocation: invocation)

    def test_ok(self):
        proxy = InvocationProxy(TestInterface.descriptor, lambda inv: 3)
        assert proxy.method(1, 2) == 3

    def test_exc(self):
        def raise_exc(invocation):
            raise TestException('Hello')
        client = proxy(TestInterface, raise_exc)

        try:
            client.method(1, 2)
            self.fail()
        except TestException as e:
            assert e == TestException('Hello')

    def test_none_result_to_default(self):
        client = InvocationProxy(TestInterface.descriptor, lambda inv: None)
        assert client.string0('hello') == ''

    def test_proxy_method(self):
        interface = TestInterface.descriptor
        method = interface.find_method('method')
        handler = lambda inv: None

        proxy = InvocationProxy(interface, handler)
        proxy_method = proxy.method

        assert method
        assert proxy_method.method is method
        assert proxy_method.handler is handler

    def test_proxy_method_chain(self):
        interface0 = TestInterface.descriptor
        method0 = interface0.find_method('interface0')
        method1 = interface0.find_method('method')
        handler = lambda inv: None

        proxy = InvocationProxy(interface0, handler)
        proxy_method = proxy.interface0(1, 2).method

        assert proxy_method.method is method1
        assert proxy_method.handler is handler
        assert proxy_method.invocation
        assert proxy_method.invocation.method is method0

    def test_invocation_chain(self):
        handler = lambda inv: inv
        proxy = InvocationProxy(TestInterface.descriptor, handler)

        invocation = proxy.interface0(1, 2).query()
        chain = invocation.to_chain()
        invocation0 = chain[0]
        invocation1 = chain[1]

        assert invocation0.method.name == 'interface0'
        assert invocation0.kwargs == {'arg0': 1, 'arg1': 2}

        assert invocation1.method.name == 'query'
        assert invocation1.kwargs == {'arg0': None, 'arg1': None}
