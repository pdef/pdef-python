# encoding: utf-8
import unittest
from pdefc.lang import *
from pdefc.generators.python import *


class TestPythonGenerator(unittest.TestCase):
    def test_init_modules(self):
        module_names = [
            'service.server',
            'service.client',
            'service.client.submodule',
            'service2.server',
            'service3'
        ]

        generator = PythonGenerator('/tmp')
        parent_names = generator._init_modules(module_names)
        assert parent_names == {'service', 'service.client', 'service2'}

    def test_filename(self):
        generator = PythonGenerator('/tmp')
        filename = generator._filename('test.service.module')
        assert filename == '/tmp/test/service/module.py'

    def test_filename__init_file(self):
        generator = PythonGenerator('/tmp')
        filename = generator._filename('test.service.module', is_init_module=True)
        assert filename == '/tmp/test/service/module/__init__.py'

    def test_render_module(self):
        msg = Message('Message')
        iface = Interface('Interface')
        enum = Enum('Enum')
        imported = Module('imported.module')

        module = Module('test', definitions=[msg, iface, enum])
        module.add_imported_module('module', imported)
        module.link()

        generator = PythonGenerator('/dev/null')
        code = generator._render_module(module)
        assert code

    def test_render_message(self):
        enum = Enum('Type')
        type0 = enum.create_value('MESSAGE')

        base = Message('Base')
        base.create_field('type', enum, is_discriminator=True)

        msg = Message('Message', base=base, discriminator_value=type0)
        msg.create_field('field', NativeType.BOOL)

        generator = PythonGenerator('/dev/null')
        code = generator._render_definition(msg)
        assert code

    def test_render_enum(self):
        enum = Enum('Number')
        enum.create_value('ONE')
        enum.create_value('TWO')
        enum.create_value('THREE')
        module = Module('test', definitions=[enum])
        module.link()

        generator = PythonGenerator('/dev/null')
        code = generator._render_definition(enum)
        assert code

    def test_render_interface(self):
        exc = Message('Exception', is_exception=True)

        iface = Interface('Interface', exc=exc)
        iface.create_method('method0', NativeType.INT32, [('arg', NativeType.INT32)])
        iface.create_method('method1', NativeType.STRING, [('name', NativeType.STRING)])

        generator = PythonGenerator('/dev/null')
        code = generator._render_definition(iface)
        assert code


class TestPythonFilters(unittest.TestCase):
    def setUp(self):
        self.filters = PythonFilters(Namespace())

    def test_pydoc(self):
        assert self.filters.pydoc(None) == ''
        assert self.filters.pydoc(' one-line ') == 'one-line'
        assert self.filters.pydoc(' \n\nmulti-\nline\n\n\n ') == '\nmulti-\nline\n\n'

    def test_pymodule(self):
        module = Module('my.test.module')
        self.filters.namespace = Namespace({'my.test': 'my_test'})

        assert self.filters.pymodule(module) == 'my_test.module'

    def test_pyref__native(self):
        for ntype in NativeType.all():
            ref = self.filters.pyref(ntype)
            assert ref is PYTHON_NATIVE_REFS[ntype.type]

    def test_pylist(self):
        list0 = List(NativeType.INT32)
        ref = self.filters.pyref(list0)

        assert ref.name == 'list'
        assert ref.descriptor == 'pdef.descriptors.list0(pdef.descriptors.int32)'

    def test_pyset(self):
        set0 = Set(NativeType.INT32)
        ref = self.filters.pyref(set0)

        assert ref.name == 'set'
        assert ref.descriptor == 'pdef.descriptors.set0(pdef.descriptors.int32)'

    def test_pymap(self):
        map0 = Map(NativeType.INT32, NativeType.INT64)
        ref = self.filters.pyref(map0)

        assert ref.name == 'dict'
        assert ref.descriptor == 'pdef.descriptors.map0(' \
                                 'pdef.descriptors.int32, ' \
                                 'pdef.descriptors.int64)'

    def test_pyenum_value(self):
        enum = Enum('Number')
        enum.create_value('ONE')
        two = enum.create_value('TWO')

        module = Module('test', definitions=[enum])
        module.link()

        ref = self.filters.pyref(two)
        assert ref.name == 'test.Number.TWO'
        assert ref.descriptor is None

    def test_pydefintion__enum(self):
        enum = Enum('Number')

        module = Module('test', definitions=[enum])
        module.link()

        ref = self.filters.pyref(enum)
        assert ref.name == 'test.Number'
        assert ref.descriptor == 'test.Number.descriptor'

    def test_pydefinition__message(self):
        def0 = Message('Message')

        module = Module('test', definitions=[def0])
        module.link()

        ref = self.filters.pyref(def0)
        assert ref.name == 'test.Message'
        assert ref.descriptor == 'test.Message.descriptor'

    def test_pydefinition__interface(self):
        def0 = Interface('Interface')

        module = Module('test', definitions=[def0])
        module.link()

        ref = self.filters.pyref(def0)
        assert ref.name == 'test.Interface'
        assert ref.descriptor == 'test.Interface.descriptor'

    def test_pydefinition__in_current_module(self):
        def0 = Message('Message')

        module = Module('test', definitions=[def0])
        module.link()

        self.filters.current_module = module
        ref = self.filters.pyref(def0)
        assert ref.name == 'Message'
        assert ref.descriptor == 'Message.descriptor'
