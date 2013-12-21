# encoding: utf-8
from __future__ import unicode_literals
from datetime import datetime
import unittest

from pdef.formats import jsonformat
from pdef.tests.inheritance.protocol import *
from pdef.tests.messages.protocol import *


class TestJsonFormat(unittest.TestCase):
    def _test(self, descriptor, parsed, serialized):
        assert jsonformat.write(parsed, descriptor) == serialized
        assert jsonformat.read(serialized, descriptor) == parsed

        # Nulls.
        assert jsonformat.write(None, descriptor) == 'null'
        assert jsonformat.read('null', descriptor) is None

    def test_boolean(self):
        self._test(descriptors.bool0, True, 'true')
        self._test(descriptors.bool0, False, 'false')

    def test_int16(self):
        self._test(descriptors.int16, -16, '-16')

    def test_int32(self):
        self._test(descriptors.int32, -32, '-32')

    def test_int64(self):
        self._test(descriptors.int64, -64, '-64')

    def test_float(self):
        self._test(descriptors.float0, -1.5, '-1.5')

    def test_double(self):
        self._test(descriptors.double0, -2.5, '-2.5')

    def test_string(self):
        self._test(descriptors.string0, '123', '"123"')
        self._test(descriptors.string0, 'привет', '"привет"')

    def test_datetime(self):
        self._test(descriptors.datetime0, datetime(2013, 11, 17, 19, 12), '"2013-11-17T19:12:00Z"')

    def test_enum(self):
        self._test(TestEnum.descriptor, TestEnum.THREE, '"three"')
        assert jsonformat.read('"tWo"', TestEnum.descriptor) == TestEnum.TWO

    def test_message(self):
        msg0 = self._complex_message()
        s = msg0.to_json()

        result = TestComplexMessage.from_json(s)
        assert msg0 == result

    def test_message__polymorphic(self):
        msg0 = self._polymorphic_message()
        s = msg0.to_json()

        result = MultiLevelSubtype.from_json(s)
        assert msg0 == result

    def test_message__skip_null_fields(self):
        message = TestMessage(string0='hello')
        assert message.to_json() == '{"string0": "hello"}'

    def test_void(self):
        self._test(descriptors.void, None, 'null')

    def _complex_message(self):
        return TestComplexMessage(
            string0="hello",
            bool0=True,
            int0=32,
            short0=16,
            long0=64,
            float0=1.5,
            double0=2.5,
            datetime0=datetime(1970, 1, 1, 0, 0, 0),
            enum0=TestEnum.THREE,
            list0=[1, 2],
            set0={1, 2},
            map0={1: 1.5},
            message0=TestMessage(
                string0='hello',
                bool0=True,
                int0=16),
            polymorphic=MultiLevelSubtype(
                field='field',
                subfield='subfield',
                mfield='mfield'))

    def _polymorphic_message(self):
        return MultiLevelSubtype(
            field='field',
            subfield='subfield',
            mfield='mfield')
