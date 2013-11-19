# encoding: utf-8
from datetime import datetime
from pdef import Type


class Descriptor(object):
    '''Base type descriptor.'''
    def __init__(self, type0, pyclass):
        self.type = type0
        self._pyclass_supplier = _supplier(pyclass)
        self._pyclass = None

        self.is_primitive = self.type in Type.PRIMITIVE_TYPES
        self.is_data_type = self.type in Type.DATA_TYPES
        self.is_message = self.type == Type.MESSAGE

    def __str__(self):
        return str(self.type)

    @property
    def pyclass(self):
        if self._pyclass is None:
            self._pyclass = self._pyclass_supplier()
        return self._pyclass


class DataTypeDescriptor(Descriptor):
    pass


class MessageDescriptor(DataTypeDescriptor):
    '''Message descriptor.'''
    def __init__(self, pyclass, base=None, discriminator_value=None, fields=None, subtypes=None):
        super(MessageDescriptor, self).__init__(Type.MESSAGE, pyclass)
        self.base = base

        self.declared_fields = tuple(fields) if fields else ()
        self.inherited_fields = base.fields if base else ()
        self.fields = self.inherited_fields + self.declared_fields

        self.discriminator_value = discriminator_value
        self.discriminator = self._find_discriminator(self.fields)

        self._subtype_suppliers = tuple(_supplier(s) for s in subtypes) if subtypes else ()
        self._subtypes = None
        self._subtype_map = None

        self.is_polymorphic = bool(self.discriminator)

    def __str__(self):
        return str(self.pyclass)

    @classmethod
    def _find_discriminator(cls, fields):
        for field in fields:
            if field.is_discriminator:
                return field

    @property
    def subtypes(self):
        if self._subtypes is None:
            self._subtypes = tuple(supplier() for supplier in self._subtype_suppliers)
            self._subtype_map = {s.discriminator_value: s for s in self._subtypes}

        return self._subtypes

    def find_field(self, name):
        '''Return a field by its name or None.'''
        for field in self.fields:
            if field.name == name:
                return field

    def find_subtype(self, type0):
        '''Return a subtype descriptor by a type enum value or self if not found.'''
        _ = self.subtypes  # Force loading subtypes.

        subtype = self._subtype_map.get(type0)
        return subtype if subtype else self


class FieldDescriptor(object):
    '''Message field descriptor.'''
    def __init__(self, name, type0, is_discriminator=False):
        self.name = name
        self._type_supplier = _supplier(type0)
        self._type = None
        self.is_discriminator = is_discriminator

    def __str__(self):
        return self.name + ' ' + self.type

    @property
    def type(self):
        '''Return field type descriptor.'''
        if self._type is None:
            self._type = self._type_supplier()
        return self._type

    def get(self, message):
        '''Get this field value in a message, check the type of the value.'''
        type0 = self.type
        return getattr(message, self.name)

    def set(self, message, value):
        '''Set this field in a message to a value, check the type of the value.'''
        type0 = self.type
        setattr(message, self.name, value)


class InterfaceDescriptor(Descriptor):
    '''Interface descriptor.'''
    def __init__(self, pyclass, exc=None, methods=None):
        super(InterfaceDescriptor, self).__init__(Type.INTERFACE, pyclass)
        self._exc_supplier = _supplier(exc)
        self._exc = None
        self.methods = tuple(methods) if methods else ()

    def __str__(self):
        return str(self.pyclass)

    @property
    def exc(self):
        if self._exc is None:
            self._exc = self._exc_supplier() if self._exc_supplier else None
        return self._exc

    def find_method(self, name):
        '''Return a method by its name or None.'''
        for method in self.methods:
            if method.name == name:
                return method


class MethodDescriptor(object):
    '''Interface method descriptor.'''
    def __init__(self, name, result, args=None, exc=None, is_post=False):
        self.name = name
        self._result_supplier = _supplier(result)
        self._result = None

        self._exc_supplier = _supplier(exc)
        self._exc = None

        self.args = tuple(args) if args else ()

        self.is_post = is_post

    @property
    def result(self):
        '''Return a result descriptor.'''
        if self._result is None:
            self._result = self._result_supplier()
        return self._result

    @property
    def exc(self):
        '''Return a expected interface exception.'''
        if self._exc is None:
            self._exc = self._exc_supplier() if self._exc_supplier else None
        return self._exc

    @property
    def is_terminal(self):
        '''Method is terminal when its result is not an interface.'''
        return self.result.type != Type.INTERFACE

    def invoke(self, obj, *args, **kwargs):
        '''Invoke this method on an object with a given arguments, return the result'''
        return getattr(obj, self.name)(*args, **kwargs)

    def __str__(self):
        '''Return a method signature as a string.'''
        s = [self.name, '(']

        next_separator = ''
        for arg in self.args:
            s.append(next_separator)
            s.append(arg.name)
            s.append(' ')
            s.append(str(arg.type))
            next_separator = ', '

        s.append(')=')
        s.append(str(self.result))

        return ''.join(s)


class ArgDescriptor(object):
    '''Method argument descriptor.'''
    def __init__(self, name, type0, is_query=False, is_post=False):
        self.name = name
        self._type_supplier = _supplier(type0)
        self._type = None

        self.is_query = is_query
        self.is_post = is_post

    @property
    def type(self):
        '''Return argument type descriptor.'''
        if self._type is None:
            self._type = self._type_supplier()
        return self._type


class EnumDescriptor(DataTypeDescriptor):
    '''Enum descriptor.'''
    def __init__(self, pyclass, values):
        super(EnumDescriptor, self).__init__(Type.ENUM, pyclass)
        self.values = tuple(v.upper() for v in values)

    def find_value(self, name):
        if name is None:
            return None
        name = name.upper()

        if name not in self.values:
            return None
        return name


class ListDescriptor(DataTypeDescriptor):
    '''Internal list descriptor.'''
    def __init__(self, element):
        super(ListDescriptor, self).__init__(Type.LIST, list)
        self.element = element

    def __str__(self):
        return 'list<%s>' % self.element


class SetDescriptor(DataTypeDescriptor):
    '''Internal set descriptor.'''
    def __init__(self, element):
        super(SetDescriptor, self).__init__(Type.SET, set)
        self.element = element

    def __str__(self):
        return 'set<%s>' % self.element


class MapDescriptor(DataTypeDescriptor):
    '''Internal map/dict descriptor.'''
    def __init__(self, key, value):
        super(MapDescriptor, self).__init__(Type.MAP, dict)
        self.key = key
        self.value = value

    def __str__(self):
        return 'map<%s, %s>' % (self.key, self.value)


def list0(element):
    '''Create a list descriptor with an element descriptor.'''
    return ListDescriptor(element)


def set0(element):
    '''Create a set descriptor with an element descriptor.'''
    return SetDescriptor(element)


def map0(key, value):
    '''Create a map (dict) descriptor with key/value descriptors.'''
    return MapDescriptor(key, value)


def message(pyclass, base=None, discriminator_value=None, fields=None, subtypes=None):
    '''Create a message descriptor.'''
    return MessageDescriptor(pyclass, base=base, discriminator_value=discriminator_value,
                             fields=fields, subtypes=subtypes)


def field(name, type0, is_discriminator=False):
    '''Create a field descriptor.'''
    return FieldDescriptor(name, type0, is_discriminator=is_discriminator)


def enum(pyclass, values):
    '''Create an enum descriptor.'''
    return EnumDescriptor(pyclass, values)


def interface(pyclass, exc=None, methods=None):
    '''Create an interface descriptor.'''
    return InterfaceDescriptor(pyclass, exc=exc, methods=methods)


def method(name, result, args=None, exc=None, is_post=False):
    '''Create an interface method descriptor.'''
    return MethodDescriptor(name, result=result, args=args, exc=exc, is_post=is_post)


def arg(name, type0, is_query=False, is_post=False):
    '''Create a method argument descriptor.'''
    return ArgDescriptor(name, type0, is_query=is_query, is_post=is_post)


def _supplier(type_or_lambda):
    if type_or_lambda is None:
        return None

    lambda0 = lambda: None
    lambda_type = type(lambda0)

    if isinstance(type_or_lambda, lambda_type) and type_or_lambda.__name__ == lambda0.__name__:
        # It is already a supplier.
        return type_or_lambda

    return lambda: type_or_lambda


bool0 = DataTypeDescriptor(Type.BOOL, bool)
int16 = DataTypeDescriptor(Type.INT16, int)
int32 = DataTypeDescriptor(Type.INT32, int)
int64 = DataTypeDescriptor(Type.INT64, int)
float0 = DataTypeDescriptor(Type.FLOAT, float)
double0 = DataTypeDescriptor(Type.DOUBLE, float)
string0 = DataTypeDescriptor(Type.STRING, unicode)
datetime0 = DataTypeDescriptor(Type.DATETIME, datetime)
void = DataTypeDescriptor(Type.VOID, type(None))
