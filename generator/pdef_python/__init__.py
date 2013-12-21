# encoding: utf-8

# Copyright: 2013 Ivan Korobkov <ivan.korobkov@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import unicode_literals
import os.path

import pdefc
from pdefc.lang import TypeEnum
from pdefc.generators import Generator, Templates, GeneratorCli, ModuleMapper

__title__ = 'pdef-java'
__author__ = 'Ivan Korobkov <ivan.korobkov@gmail.com>'
__license__ = 'Apache License 2.0'
__copyright__ = 'Copyright 2013 Ivan Korobkov'


UTF8 = 'utf-8'
PYMODULE = '.protocol'
GENERATED_BY = '# Generated by Pdef compiler %s. DO NOT EDIT.' % pdefc.__version__

MODULE_TEMPLATE = 'module.jinja2'
DEFINITION_TEMPLATES = {
    TypeEnum.ENUM:      'enum.jinja2',
    TypeEnum.MESSAGE:   'message.jinja2',
    TypeEnum.INTERFACE: 'interface.jinja2'
}


class PythonGeneratorCli(GeneratorCli):
    def build_parser(self, parser):
        self._add_module_args(parser)

    def create_generator(self, out, args):
        module_names = self._parse_module_args(args)
        return PythonGenerator(out, module_names)


class PythonGenerator(Generator):
    '''Python code generator, supports module names, does not support prefixes.'''

    @classmethod
    def create_cli(cls):
        return PythonGeneratorCli()

    def __init__(self, out, module_names=None):
        super(PythonGenerator, self).__init__(out)

        self.module_mapper = ModuleMapper(module_names)
        self.filters = _PythonFilters(self.module_mapper)
        self.templates = Templates(__file__, filters=self.filters)

    def generate(self, package):
        self._generate_modules(package.modules)
        self._generate_init_files(package.modules)

    def _generate_modules(self, modules):
        for module in modules:
            code = self._render_module(module)
            filename = self._filename(module)

            self.write_file(filename, code)

    def _generate_init_files(self, modules):
        for module in modules:
            filename = self._init_filename(module)
            filepath = os.path.join(self.out, filename)

            if not os.path.exists(filepath):
                self.write_file(filename, '# encoding: utf-8')

    def _render_module(self, module):
        # Render module definitions.
        definitions = [self._render_definition(d) for d in module.definitions]

        # Render the module.
        return self.templates.render(MODULE_TEMPLATE, imported_modules=module.imported_modules,
                                     definitions=definitions, generated_by=GENERATED_BY)

    def _render_definition(self, def0):
        tname = DEFINITION_TEMPLATES.get(def0.type)
        if not tname:
            raise ValueError('Unsupported definition %r' % def0)

        template = self.templates.get(tname)
        try:
            self.filters.current_module = def0.module
            if def0.is_enum:
                return template.render(enum=def0)
            elif def0.is_message:
                return template.render(message=def0)
            else:
                return template.render(interface=def0)
        finally:
            self.filters.current_module = None

    def _filename(self, module):
        path = self.filters.pymodule(module)
        return path.replace('.', '/') + '.py'

    def _init_filename(self, module):
        filename = self._filename(module)
        path = os.path.dirname(filename)
        return os.path.join(path, '__init__.py')


class _PythonFilters(object):
    def __init__(self, module_mapper):
        self.module_mapper = module_mapper
        self.current_module = None

    def pydoc(self, doc):
        if not doc:
            return ''

        # Escape python docstrings delimiters,
        # and strip empty characters.
        s = doc.replace('"""', '\"\"\"').strip()

        if '\n' not in s:
            # It's a one-line comment.
            return s

        # It's a multi-line comment.
        return '\n' + s + '\n\n'

    def pymodule(self, module):
        name = self.module_mapper(module.fullname)
        return name + PYMODULE

    def pymessage_base(self, message):
        if message.base:
            return self.pyref(message.base)
        return 'pdef.Exc' if message.is_exception else 'pdef.Message'

    def pybool(self, expr):
        return 'True' if expr else 'False'

    def pydescriptor(self, type0):
        return self.pyref(type0).descriptor

    def pyref(self, type0):
        if type0 is None:
            return _PythonRef('None', None)

        if type0.is_native:
            return PYTHON_NATIVE_REFS[type0.type]

        switch = {
            TypeEnum.LIST: self._pylist,
            TypeEnum.SET: self._pyset,
            TypeEnum.MAP: self._pymap,
            TypeEnum.ENUM_VALUE: self._pyenum_value
        }

        factory = switch.get(type0.type, self._pydefinition)
        return factory(type0)

    def _pylist(self, type0):
        element = self.pyref(type0.element)
        descriptor = 'descriptors.list0(%s)' % element.descriptor

        return _PythonRef('list', descriptor)

    def _pyset(self, type0):
        element = self.pyref(type0.element)
        descriptor = 'descriptors.set0(%s)' % element.descriptor

        return _PythonRef('set', descriptor)

    def _pymap(self, type0):
        key = self.pyref(type0.key)
        value = self.pyref(type0.value)
        descriptor = 'descriptors.map0(%s, %s)' % (key.descriptor, value.descriptor)

        return _PythonRef('dict', descriptor)

    def _pyenum_value(self, type0):
        enum = self.pyref(type0.enum)
        name = '%s.%s' % (enum.name, type0.name)

        return _PythonRef(name, None)

    def _pydefinition(self, type0):
        if type0.module == self.current_module:
            # The definition is referenced from the declaring module.
            name = type0.name
        else:
            module_name = self.pymodule(type0.module)
            name = '%s.%s' % (module_name, type0.name)

        descriptor = '%s.descriptor' % name
        return _PythonRef(name, descriptor)


class _PythonRef(object):
    def __init__(self, name, descriptor):
        self.name = name
        self.descriptor = descriptor

    def __str__(self):
        return str(self.name)


PYTHON_NATIVE_REFS = {
    TypeEnum.BOOL: _PythonRef('bool', 'descriptors.bool0'),
    TypeEnum.INT16: _PythonRef('int', 'descriptors.int16'),
    TypeEnum.INT32: _PythonRef('int', 'descriptors.int32'),
    TypeEnum.INT64: _PythonRef('int', 'descriptors.int64'),
    TypeEnum.FLOAT: _PythonRef('float', 'descriptors.float0'),
    TypeEnum.DOUBLE: _PythonRef('float', 'descriptors.double0'),
    TypeEnum.STRING: _PythonRef('unicode', 'descriptors.string0'),
    TypeEnum.DATETIME: _PythonRef('datetime', 'descriptors.datetime0'),
    TypeEnum.VOID: _PythonRef('object', 'descriptors.void'),
}
