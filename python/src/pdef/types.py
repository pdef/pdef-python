# encoding: utf-8
import copy
import pdef


class Type(object):
    '''Pdef type enum.'''

    # Primitive types
    BOOL = 'bool'
    INT16 = 'int16'
    INT32 = 'int32'
    INT64 = 'int64'
    FLOAT = 'float'
    DOUBLE = 'double'
    STRING = 'string'
    DATETIME = 'datetime'

    # Void
    VOID = 'void'

    # Collection types.
    LIST = 'list'
    MAP = 'map'
    SET = 'set'

    # User defined types.
    ENUM = 'enum'
    MESSAGE = 'message'
    INTERFACE = 'interface'

    PRIMITIVE_TYPES = (BOOL, INT16, INT32, INT64, FLOAT, DOUBLE, STRING)
    DATA_TYPES = PRIMITIVE_TYPES + (DATETIME, LIST, MAP, SET, ENUM, MESSAGE, VOID)
    ALL_TYPES = DATA_TYPES + (INTERFACE, )
    MUTABLE_TYPES = (LIST, MAP, SET, MESSAGE)


class Enum(object):
    descriptor = None


class Interface(object):
    descriptor = None


class Message(object):
    descriptor = None

    @classmethod
    def from_json(cls, s, **kwargs):
        '''Parse a message from a json string.'''
        return pdef.jsonformat.read(s, cls.descriptor, **kwargs)

    @classmethod
    def from_json_stream(cls, fp, **kwargs):
        '''Parse a message from a json file-like object.'''
        return pdef.jsonformat.read_stream(fp, cls.descriptor, **kwargs)

    @classmethod
    def from_dict(cls, d):
        '''Parse a message from a dictionary.'''
        return pdef.jsonformat.read_object(d, cls.descriptor)

    def to_json(self, indent=None, **kwargs):
        '''Convert this message to a json string.'''
        return pdef.jsonformat.write(self, self.descriptor, indent=indent)

    def to_json_stream(self, fp, indent=None, **kwargs):
        '''Serialize this message as a json string to a file-like stream.'''
        return pdef.jsonformat.write_to_stream(self, self.descriptor, fp, indent=indent, **kwargs)

    def to_dict(self):
        '''Convert this message to a dictionary (serialize each field).'''
        return pdef.jsonformat.write_object(self, self.descriptor)

    def merge(self, message):
        '''Deep copy present fields from another message into this one.'''
        if not message:
            return

        descriptor = self.descriptor
        if not isinstance(message, self.__class__):
            if not isinstance(self, message.__class__):
                return
            descriptor = message.descriptor

        for field in descriptor.fields:
            if field.is_discriminator:
                continue

            value = getattr(message, field.private_name)
            if value is None:
                continue

            value_copy = copy.deepcopy(value)
            setattr(self, field.name, value_copy)

        return self

    def merge_dict(self, d):
        '''Parse a message from a dict and merge it into this message.'''
        message = self.__class__.from_dict(d)
        return self.merge(message)

    def merge_json(self, s):
        '''Parse a message from a json string and merge it into this message.'''
        message = self.__class__.from_json(s)
        return self.merge(message)

    def merge_json_stream(self, stream):
        '''Parse a message from a file-like object with json data and merge it into this message.'''
        message = self.__class__.from_json_stream(stream)
        return self.merge(message)

    def __eq__(self, other):
        if other is None or self.__class__ is not other.__class__:
            return False
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return unicode(self).encode('utf-8', errors='replace')

    def __copy__(self):
        msg = self.__class__()
        msg.__dict__ = copy.copy(self.__dict__)
        return msg

    def __deepcopy__(self, memo=None):
        msg = self.__class__()
        msg.__dict__ = copy.deepcopy(self.__dict__, memo)
        return msg

    def __unicode__(self):
        s = [u'<', self.__class__.__name__, u' ']

        first = True
        d = self.__dict__
        for key, value in d.items():
            if first:
                first = False
            else:
                s.append(u', ')

            s.append(key)
            s.append('=')
            s.append(unicode(value))

        s.append(u'>')
        return u''.join(s)


class Exc(Exception, Message):
    pass
