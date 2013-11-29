# encoding: utf-8
from datetime import datetime
import json as _json
import pdef.types

SIMPLE_ISO_8601_PATTERN = "%Y-%m-%dT%H:%M:%SZ"


class JsonFormat(object):
    '''JsonFormat parses/serializes Pdef types from/to JSON.'''

    def __init__(self):
        self.object_format = _JsonObjectFormat()

    def read(self, s, descriptor):
        '''Read a pdef object from a JSON string.'''
        if s is None:
            return None

        value = _json.loads(s)
        parsed = self.object_format.read(value, descriptor)
        return parsed

    def read_stream(self, fp, descriptor):
        '''Read a pdef object from a a JSON file-like object.'''
        value = _json.load(fp)
        parsed = self.object_format.read(value, descriptor)
        return parsed

    def read_object(self, data, descriptor):
        '''Read a pdef object from a JSON-compatible object.'''
        return self.object_format.read(data, descriptor)

    def write(self, obj, descriptor, indent=None, **kwargs):
        '''Write a pdef object to a JSON string.'''
        serialized = self.object_format.write(obj, descriptor)
        s = _json.dumps(serialized, ensure_ascii=False, indent=indent, **kwargs)
        return s

    def write_to_stream(self, obj, descriptor, fp, indent=None, **kwargs):
        '''Write a pdef object as a JSON string to a file-like object.'''
        serialized = self.object_format.write(obj, descriptor)
        return _json.dump(serialized, fp, ensure_ascii=False, indent=indent, **kwargs)

    def write_object(self, obj, descriptor):
        '''Write a pdef object into a JSON-compatible object.'''
        return self.object_format.write(obj, descriptor)


class _JsonObjectFormat(object):
    '''JsonObjectFormat parses/serializes Pdef objects from/to JSON-compatible objects.'''

    def write(self, obj, descriptor):
        '''Write an object to a native python type.'''
        if obj is None:
            return None

        type0 = descriptor.type
        if type0 in pdef.types.Type.PRIMITIVE_TYPES:
            # This is for type checks.
            return descriptor.pyclass(obj)

        write = self.write
        write_key = self._write_key
        Type = pdef.types.Type

        if type0 == Type.DATETIME:
            if not isinstance(obj, datetime):
                raise ValueError('Not a datetime object %r' % datetime)
            return obj.strftime(SIMPLE_ISO_8601_PATTERN)

        elif type0 == Type.ENUM:
            return obj.lower()

        elif type0 == Type.LIST:
            elemd = descriptor.element
            return [write(elem, elemd) for elem in obj]

        elif type0 == Type.SET:
            elemd = descriptor.element
            return [write(elem, elemd) for elem in obj]

        elif type0 == Type.MAP:
            keyd = descriptor.key
            valued = descriptor.value
            return {write_key(k, keyd): write(v, valued) for k, v in obj.items() if k is not None}

        elif type0 == Type.MESSAGE:
            return self._message_to_dict(obj)

        elif type0 == Type.VOID:
            return None

        raise ValueError('Unsupported type ' + descriptor)

    def _write_key(self, key, keyd):
        if key is None:
            raise ValueError('None dict key')

        type0 = keyd.type
        Type = pdef.types.Type

        if type0 == Type.BOOL:
            return 'true' if key else 'false'

        elif type0 in Type.PRIMITIVE_TYPES:
            return str(key)

        elif type0 == Type.DATETIME:
            return key.strftime(SIMPLE_ISO_8601_PATTERN)

        raise ValueError('Unsupported key type ' + keyd)

    def _message_to_dict(self, message):
        if message is None:
            return None

        result = {}
        to_object = self.write
        descriptor = message.descriptor  # Support polymorphic messages.

        # field_tuples and private names are a performance optimization.
        # It's about 30% faster.
        for name, private_name, type0 in descriptor.field_tuples:
            value = getattr(message, private_name)
            if value is None:
                continue

            result[name] = to_object(value, type0)
        return result

    def read(self, data, descriptor):
        '''Read a pdef object from a native python type.'''
        if data is None:
            return None

        type0 = descriptor.type
        Type = pdef.types.Type
        read = self.read

        if type0 in Type.PRIMITIVE_TYPES:
            return descriptor.pyclass(data)

        elif type0 == Type.DATETIME:
            if isinstance(data, datetime):
                return data
            return datetime.strptime(data, SIMPLE_ISO_8601_PATTERN)

        elif type0 == Type.ENUM:
            return descriptor.find_value(data)

        elif type0 == Type.LIST:
            elemd = descriptor.element
            return [read(elem, elemd) for elem in data]

        elif type0 == Type.SET:
            elemd = descriptor.element
            return {read(elem, elemd) for elem in data}

        elif type0 == Type.MAP:
            keyd = descriptor.key
            valued = descriptor.value
            return {read(k, keyd): read(v, valued) for k, v in data.items()}

        elif type0 == Type.MESSAGE:
            return self._message_from_dict(data, descriptor)

        elif type0 == Type.VOID:
            return None

        raise ValueError('Unsupported type ' + descriptor)

    def _message_from_dict(self, dict0, descriptor):
        '''Parse a message from a dictionary.'''
        if dict0 is None:
            return None

        from_object = self.read

        if descriptor.is_polymorphic:
            # Parse a discriminator value and find a subtype descriptor.
            discriminator = descriptor.discriminator
            serialized = dict0.get(discriminator.name)
            parsed = from_object(serialized, discriminator.type)
            descriptor = descriptor.find_subtype(parsed)

        message = descriptor.pyclass()
        for field in descriptor.fields:
            serialized = dict0.get(field.name)
            if serialized is None:
                continue

            parsed = from_object(serialized, field.type)
            setattr(message, field.name, parsed)

        return message


jsonformat = JsonFormat()
