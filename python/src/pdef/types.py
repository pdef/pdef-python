# encoding: utf-8
import copy
import pdef.formats


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


class Enum(object):
    descriptor = None

    @classmethod
    def parse_json(cls, s):
        return pdef.json_format.from_json(s, cls.descriptor)


class Interface(object):
    descriptor = None


class Message(object):
    descriptor = None

    @classmethod
    def from_json(cls, s, **kwargs):
        '''Parse a message from a json string.'''
        return pdef.json_format.from_json(s, cls.descriptor, **kwargs)

    @classmethod
    def from_json_stream(cls, fp, **kwargs):
        '''Parse a message from a json file-like object.'''
        return pdef.json_format.from_json_stream(fp, cls.descriptor, **kwargs)

    @classmethod
    def from_dict(cls, d):
        '''Parse a message from a dictionary.'''
        return pdef.object_format.from_object(d, cls.descriptor)

    def to_json(self, indent=None, **kwargs):
        '''Convert this message to a json string.'''
        return pdef.json_format.to_json(self, self.descriptor, indent=indent)

    def to_json_stream(self, fp, indent=None, **kwargs):
        '''Serialize this message as a json string to a file-like stream.'''
        return pdef.json_format.to_json_stream(self, self.descriptor, fp, indent=indent, **kwargs)

    def to_dict(self):
        '''Convert this message to a dictionary (serialize each field).'''
        return pdef.object_format.to_object(self, self.descriptor)

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
        for field in self.descriptor.fields:
            value = field.get(self)
            if value is None:
                continue

            if first:
                first = False
            else:
                s.append(u', ')

            s.append(field.name)
            s.append('=')
            s.append(unicode(value))
        s.append(u'>')
        return u''.join(s)


class Exc(Exception, Message):
    pass
