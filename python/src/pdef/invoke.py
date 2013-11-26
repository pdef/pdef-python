# encoding: utf-8
import copy
from collections import deque


def proxy(interface, invocation_handler):
    '''Create a interface proxy.

    The proxy captures method calls into chained invocations, and passes them
    to the handler on terminal methods.

    @param interface:               Interface with a class descriptor field.
    @param invocation_handler:      callable(Invocation): InvocationResult.
    '''
    descriptor = interface.descriptor
    return InvocationProxy(descriptor, invocation_handler)


class Invocation(object):
    '''Immutable chained method invocation.'''
    @classmethod
    def root(cls, method, *args, **kwargs):
        return Invocation(method, args=args, kwargs=kwargs)

    def __init__(self, method, args=None, kwargs=None, parent=None):
        '''Create an invocation.

        @param method: a method descriptor.
        @param parent: a parent invocation, nullable.
        '''
        self.method = method
        self.parent = parent

        self.kwargs = self._build_kwargs(method, args, kwargs) if method else {}
        self.kwargs = copy.deepcopy(self.kwargs)    # Make defensive copies.

    def __repr__(self):
        return '<Invocation %r args=%r>' % (self.method.name, self.kwargs)

    def next(self, method, *args, **kwargs):
        '''Create a child invocation.'''
        return Invocation(method, args=args, kwargs=kwargs, parent=self)

    def to_chain(self):
        '''Return a list of invocations.'''
        if not self.parent:
            return [self]

        chain = self.parent.to_chain()
        chain.append(self)
        return chain

    def invoke(self, obj):
        '''Invoke this invocation chain on an object.'''
        chain = self.to_chain()

        for inv in chain:
            obj = inv.method.invoke(obj, **inv.kwargs)

        return obj

    @staticmethod
    def _build_kwargs(method, args=None, kwargs=None):
        '''Convert args and kwargs into a param dictionary, check their number and types.'''
        def wrong_args():
            return TypeError('Wrong method arguments, %s, got args=%s, kwargs=%s' %
                             (method, args, kwargs))
        params = {}
        args = args if args else ()
        kwargs = kwargs if kwargs else {}
        method_args = deque(method.args)

        # Check that the number of args and kwargs is less or equal to the method args number.
        if len(method_args) < (len(args) + len(kwargs)):
            raise wrong_args()

        # Consume all positional arguments.
        for value in args:
            argd = method_args.popleft()
            params[argd.name] = value

        # Add keyword arguments using the remaining method args.
        consumed_kwargs = {}
        for argd in method_args:
            if argd.name not in kwargs:
                params[argd.name] = None
                continue

            value = kwargs.get(argd.name)
            params[argd.name] = value
            consumed_kwargs[argd.name] = value

        # Check that all kwargs have been consumed.
        if consumed_kwargs.keys() != kwargs.keys():
            raise wrong_args()

        return params


class InvocationProxy(object):
    '''Reflective client proxy.'''
    def __init__(self, descriptor, handler, invocation=None):
        self._descriptor = descriptor
        self._handler = handler
        self._invocation = invocation

    def __repr__(self):
        return '<InvocationProxy %s>' % self._descriptor

    def __getattr__(self, name):
        '''Return a proxy method.'''
        method = self._descriptor.find_method(name)
        if not method:
            raise AttributeError('Method not found %r' % name)

        return _ProxyMethod(self._invocation, self._handler, method)


class _ProxyMethod(object):
    def __init__(self, invocation, handler, method):
        self.invocation = invocation
        self.handler = handler
        self.method = method

    def __repr__(self):
        return '<ProxyMethod %r>' % self.method.name

    def __call__(self, *args, **kwargs):
        method = self.method
        if self.invocation:
            invocation = self.invocation.next(method, *args, **kwargs)
        else:
            invocation = Invocation(method, args=args, kwargs=kwargs)

        if not method.is_terminal:
            # This is a method, which returns an interface.
            # Create a next invocation proxy.
            return InvocationProxy(method.result, self.handler, invocation)

        # The method result is a value or void.
        return self.handler(invocation)
