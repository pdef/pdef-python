# encoding: utf-8
import copy
import unittest

from pdef.tests.inheritance.protocol import *
from pdef.tests.messages.protocol import *


class TestPdefMessage(unittest.TestCase):
    JSON = '''{"string0": "hello", "bool0": true}'''

    def _fixture(self):
        return TestMessage(string0="hello", bool0=True)

    def _fixture_dict(self):
        return {'string0': 'hello', 'bool0': True}

    def test_parse_json(self):
        msg = TestMessage.from_json(self.JSON)
        assert msg == self._fixture()

    def test_parse_dict(self):
        msg = self._fixture()
        d = msg.to_dict()

        msg1 = TestMessage.from_dict(d)
        assert msg == msg1

    def test_to_json(self):
        msg = self._fixture()
        s = msg.to_json()

        msg1 = TestMessage.from_json(s)
        assert msg == msg1

    def test_to_dict(self):
        d = self._fixture().to_dict()

        assert d == self._fixture_dict()

    def test_merge(self):
        message = TestMessage()
        message.merge(self._fixture())

        assert message == self._fixture()

    def test_merge__supertype(self):
        base = Base(field='hello')
        subtype = MultiLevelSubtype()
        subtype.merge(base)

        assert subtype.field == 'hello'

    def test_merge__subtype(self):
        subtype = MultiLevelSubtype(field='hello')
        base = Base()
        base.merge(subtype)

        assert base.field == 'hello'

    def test_merge__skip_discriminators(self):
        subtype = Subtype()
        assert subtype.type == PolymorphicType.SUBTYPE

        msubtype = MultiLevelSubtype()
        assert msubtype.type == PolymorphicType.MULTILEVEL_SUBTYPE

        msubtype.merge(subtype)
        assert msubtype.type == PolymorphicType.MULTILEVEL_SUBTYPE

    def test_merge_dict(self):
        message = TestMessage()
        message.merge_dict(self._fixture_dict())

        assert message == self._fixture()

    def merge_json(self):
        message = TestMessage()
        message.merge_json(self._fixture().to_json())

        assert message == self._fixture()

    def test_eq(self):
        msg0 = self._fixture()
        msg1 = self._fixture()
        assert msg0 == msg1

        msg1.string0 = 'qwer'
        assert msg0 != msg1

    def test_copy(self):
        msg0 = TestComplexMessage(string0='hello', list0=[1,2,3], message0=TestMessage('world'))
        msg1 = copy.copy(msg0)

        assert msg1 is not msg0
        assert msg1 == msg0
        assert msg1.list0 is msg0.list0
        assert msg1.message0 is msg0.message0

    def test_deepcopy(self):
        msg0 = TestComplexMessage(string0='hello', list0=[1,2,3], message0=TestMessage('world'))
        msg1 = copy.deepcopy(msg0)

        assert msg1 is not msg0
        assert msg1 == msg0
        assert msg1.list0 is not msg0.list0
        assert msg1.message0 is not msg0.message0
