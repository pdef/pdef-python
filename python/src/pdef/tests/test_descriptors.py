# encoding: utf-8
from __future__ import unicode_literals
import unittest
from mock import Mock

from pdef.tests.inheritance.protocol import *
from pdef.tests.interfaces.protocol import *
from pdef.tests.messages.protocol import *


class TestMessageDescriptor(unittest.TestCase):
    def test(self):
        descriptor = TestMessage.descriptor

        assert descriptor.pyclass is TestMessage
        assert descriptor.base is None
        assert descriptor.discriminator is None
        assert descriptor.discriminator_value is None
        assert len(descriptor.subtypes) == 0
        assert len(descriptor.fields) == 3

    def test__nonpolymorphic_inheritance(self):
        base = TestMessage.descriptor
        descriptor = TestComplexMessage.descriptor

        assert descriptor.pyclass is TestComplexMessage
        assert descriptor.base is TestMessage.descriptor
        assert descriptor.inherited_fields == base.fields
        assert descriptor.fields == base.fields + descriptor.declared_fields
        assert len(descriptor.subtypes) == 0

    def test__polymorphic_inheritance(self):
        base = Base.descriptor
        subtype = Subtype.descriptor
        subtype2 = Subtype2.descriptor
        msubtype = MultiLevelSubtype.descriptor
        discriminator = base.find_field('type')

        assert base.base is None
        assert subtype.base is base
        assert subtype2.base is base
        assert msubtype.base is subtype

        assert base.discriminator is discriminator
        assert subtype.discriminator is discriminator
        assert subtype2.discriminator is discriminator
        assert msubtype.discriminator is discriminator

        assert base.discriminator_value is None
        assert subtype.discriminator_value is PolymorphicType.SUBTYPE
        assert subtype2.discriminator_value is PolymorphicType.SUBTYPE2
        assert msubtype.discriminator_value is PolymorphicType.MULTILEVEL_SUBTYPE

        assert set(base.subtypes) == {subtype, subtype2, msubtype}
        assert set(subtype.subtypes) == {msubtype}
        assert not subtype2.subtypes
        assert not msubtype.subtypes

        assert base.find_subtype(None) is base
        assert base.find_subtype(PolymorphicType.SUBTYPE) is subtype
        assert base.find_subtype(PolymorphicType.SUBTYPE2) is subtype2
        assert base.find_subtype(PolymorphicType.MULTILEVEL_SUBTYPE) is msubtype


class TestFieldDescriptor(unittest.TestCase):
    def test(self):
        string0 = TestMessage.string0
        bool0 = TestMessage.bool0

        assert string0.name == 'string0'
        assert string0.type is descriptors.string0

        assert bool0.name == 'bool0'
        assert bool0.type is descriptors.bool0

    def test_discriminator(self):
        field = Base.type

        assert field.name == 'type'
        assert field.type is PolymorphicType.descriptor
        assert field.is_discriminator

    def test_default_value(self):
        message = TestMessage()
        assert message.string0 == ''
        assert not message.has_string0

        message.string0 = 'hello'
        assert message.string0 == 'hello'
        assert message.has_string0

    def test_default_value__set_mutable(self):
        message = TestComplexMessage()
        assert not message.has_list0
        assert not message.has_set0
        assert not message.has_map0
        assert not message.has_message0

        list0 = message.list0
        set0 = message.set0
        map0 = message.map0
        message0 = message.message0
        assert list0 == []
        assert set0 == set()
        assert map0 == {}
        assert message0 == TestMessage()

        assert message.list0 is list0
        assert message.set0 is set0
        assert message.map0 is map0
        assert message.message0 is message0

    def test_python_descriptor_protocol(self):
        class A(object):
            field = descriptors.field('field', lambda: descriptors.string0)
            has_field = field.has_property
            def __init__(self, field=None):
                self.field = field

        a = A()
        assert a.field == ''
        assert a.has_field is False

        a.field = 'hello'
        assert a.field == 'hello'
        assert a.has_field


class TestInterfaceDescriptor(unittest.TestCase):
    def test(self):
        descriptor = TestInterface.descriptor
        method = descriptor.find_method('method')

        assert descriptor.pyclass is TestInterface
        assert descriptor.exc is TestException.descriptor
        assert len(descriptor.methods) == 13
        assert method

    def test_inheritance(self):
        base = TestInterface.descriptor
        descriptor = TestSubInterface.descriptor

        assert descriptor.base is base
        assert len(descriptor.methods) == (len(base.methods) + 1)
        assert descriptor.find_method('subMethod')
        assert descriptor.exc is TestException.descriptor


class TestMethodDescriptor(unittest.TestCase):
    def test(self):
        method = TestInterface.descriptor.find_method('message0')

        assert method.name == 'message0'
        assert method.result is TestMessage.descriptor
        assert len(method.args) == 1
        assert method.args[0].name == 'msg'
        assert method.args[0].type is TestMessage.descriptor

    def test_args(self):
        method = TestInterface.descriptor.find_method('method')

        assert len(method.args) == 2
        assert method.args[0].name == 'arg0'
        assert method.args[1].name == 'arg1'
        assert method.args[0].type is descriptors.int32
        assert method.args[1].type is descriptors.int32

    def test_post_terminal(self):
        descriptor = TestInterface.descriptor
        method = descriptor.find_method('method')
        post = descriptor.find_method('post')
        interface = descriptor.find_method('interface0')

        assert method.is_terminal
        assert not method.is_post

        assert post.is_terminal
        assert post.is_post

        assert not interface.is_terminal
        assert not interface.is_post

    def test_invoke(self):
        service = Mock()
        method = TestInterface.descriptor.find_method('method')
        method.invoke(service, 1, arg1=2)
        service.method.assert_called_with(1, arg1=2)


class TestEnumDescriptor(unittest.TestCase):
    def test(self):
        descriptor = TestEnum.descriptor
        assert descriptor.values == ('ONE', 'TWO', 'THREE')

    def test_find_value(self):
        descriptor = TestEnum.descriptor
        assert descriptor.find_value('one') == TestEnum.ONE
        assert descriptor.find_value('TWO') == TestEnum.TWO


class TestListDescriptor(unittest.TestCase):
    def test(self):
        list0 = descriptors.list0(descriptors.string0)
        assert list0.element is descriptors.string0


class TestSetDescriptor(unittest.TestCase):
    def test(self):
        set0 = descriptors.set0(descriptors.int32)
        assert set0.element is descriptors.int32


class TestMapDescriptor(unittest.TestCase):
    def test(self):
        map0 = descriptors.map0(descriptors.string0, descriptors.int32)
        assert map0.key is descriptors.string0
        assert map0.value is descriptors.int32
