# Copyright 2023 TryExceptElse
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject
# to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test module containing Parser tests.
"""
import pytest

from ..parser import (
    Parser, Field, Annotation, parse_annotations, parse_fields
)
from ..interface import Serializable, Method, Parameter
from .util import get_resource


class TestParser:
    """Contains Parser tests."""

    def test_simple_enum(self):
        header = get_resource('serializable/enum.h')
        profile = Parser().parse([header])
        mode = profile.serializable_types['Mode']
        assert mode.type == Serializable.Type.ENUM

    def test_enum_class(self):
        header = get_resource('serializable/enum_class.h')
        profile = Parser().parse([header])
        mode = profile.serializable_types['Mode']
        assert mode.type == Serializable.Type.ENUM

    def test_simple_struct(self):
        header = get_resource('serializable/struct.h')
        profile = Parser().parse([header])
        foo = profile.serializable_types['Foo']
        assert foo.type == Serializable.Type.STRUCT
        id_field = foo.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = foo.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'

    def test_simple_class(self):
        header = get_resource('serializable/class.h')
        profile = Parser().parse([header])
        foo = profile.serializable_types['Foo']
        assert foo.type == Serializable.Type.STRUCT
        id_field = foo.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = foo.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'

    def test_struct_aggregate(self):
        header = get_resource('serializable/struct_aggregate.h')
        profile = Parser().parse([header])
        foo = profile.serializable_types['Foo']
        assert foo.type == Serializable.Type.STRUCT
        for field_name in 'a', 'b', 'c':
            id_field = foo.fields[field_name]
            assert id_field.name == field_name
            assert id_field.type_name == 'std::int32_t'

    def test_struct_on_single_line(self):
        header = get_resource('serializable/struct_inline.h')
        profile = Parser().parse([header])
        foo = profile.serializable_types['Foo']
        assert foo.type == Serializable.Type.STRUCT
        id_field = foo.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = foo.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'

    def test_struct_with_defaults(self):
        header = get_resource('serializable/struct_with_defaults.h')
        profile = Parser().parse([header])
        foo = profile.serializable_types['Foo']
        assert foo.type == Serializable.Type.STRUCT
        id_field = foo.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = foo.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'

    def test_class_with_methods(self):
        header = get_resource('serializable/class_with_methods.h')
        profile = Parser().parse([header])
        foo = profile.serializable_types['Foo']
        assert foo.type == Serializable.Type.STRUCT
        id_field = foo.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = foo.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'

    def test_namespaced_serializable(self):
        header = get_resource('serializable/namespaced_struct.h')
        profile = Parser().parse([header])
        foo = profile.serializable_types['bar::baz::Foo']
        assert foo.type == Serializable.Type.STRUCT
        id_field = foo.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = foo.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'

    def test_nested_serializable(self):
        header = get_resource('serializable/nested_struct.h')
        profile = Parser().parse([header])
        foo = profile.serializable_types['bar::Interface::Foo']
        assert foo.type == Serializable.Type.STRUCT
        id_field = foo.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = foo.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'

    def test_accessor_method(self):
        header = get_resource('method/accessor.h')
        profile = Parser().parse([header])
        interface = profile.interfaces['Interface']
        assert interface.name == 'Interface'
        accessor = interface.methods['access()const']
        assert accessor == Method(
            name='access()const',
            return_type='int',
            parameters=[],
        )

    def test_binary_method(self):
        header = get_resource('method/binary.h')
        profile = Parser().parse([header])
        interface = profile.interfaces['Interface']
        assert interface.name == 'Interface'
        accessor = interface.methods['DoTheThing(std::string,int)const']
        assert accessor == Method(
            name='DoTheThing(std::string,int)const',
            return_type='int',
            parameters=[
                Parameter(name='foo', type='std::string'),
                Parameter(name='baz', type='int'),
            ],
        )

    def test_consumer_method(self):
        header = get_resource('method/consumer.h')
        profile = Parser().parse([header])
        interface = profile.interfaces['Interface']
        assert interface.name == 'Interface'
        accessor = interface.methods['DoTheThing(std::int32_t)const']
        assert accessor == Method(
            name='DoTheThing(std::int32_t)const',
            return_type='void',
            parameters=[Parameter(name='foo', type='std::int32_t')],
        )

    def test_method_with_default_impl(self):
        header = get_resource('method/default_impl.h')
        profile = Parser().parse([header])
        interface = profile.interfaces['Interface']
        assert interface.name == 'Interface'
        accessor = interface.methods['DoTheThing(std::int32_t)const']
        assert accessor == Method(
            name='DoTheThing(std::int32_t)const',
            return_type='void',
            parameters=[Parameter(name='foo', type='std::int32_t')],
        )

    def test_multiline_method(self):
        header = get_resource('method/multiline.h')
        profile = Parser().parse([header])
        interface = profile.interfaces['Interface']
        assert interface.name == 'Interface'
        accessor = interface.methods['DoTheThing(int,int)const']
        assert accessor == Method(
            name='DoTheThing(int,int)const',
            return_type='int',
            parameters=[Parameter(name='foo', type='std::int32_t')],
        )

    def test_optional_param_method(self):
        header = get_resource('method/optional_param.h')
        profile = Parser().parse([header])
        interface = profile.interfaces['Interface']
        assert interface.name == 'Interface'
        accessor_a = interface.methods['DoTheThing(int)']
        assert accessor_a == Method(
            name='DoTheThing(int)',
            return_type='int',
            parameters=[Parameter(name='foo', type='int')],
        )
        accessor_b = interface.methods['DoTheThing(int)']
        assert accessor_b == Method(
            name='DoTheThing(int,int)',
            return_type='int',
            parameters=[
                Parameter(name='foo', type='int'),
                Parameter(name='flags', type='int'),
            ],
        )

    def test_overloaded_method(self):
        header = get_resource('method/overloaded_method.h')
        profile = Parser().parse([header])
        interface = profile.interfaces['Interface']
        assert interface.name == 'Interface'
        assert interface.methods['Encode(std::string)const'] == Method(
            name='DoTheThing(std::string)const',
            return_type='int',
            parameters=[Parameter(name='x', type='std::string')],
        )
        assert interface.methods['Encode(std::int32_t)const'] == Method(
            name='DoTheThing(std::string)const',
            return_type='int',
            parameters=[Parameter(name='x', type='std::int32_t')],
        )

    def test_unary_method(self):
        header = get_resource('method/unary.h')
        profile = Parser().parse([header])
        interface = profile.interfaces['Interface']
        assert interface.name == 'Interface'
        accessor = interface.methods['Encode(int)const']
        assert accessor == Method(
            name='Encode(int)const',
            return_type='int',
            parameters=[Parameter(name='foo', type='int')],
        )

    def test_namespaced_interface(self):
        header = get_resource('method/namespace.h')
        profile = Parser().parse([header])
        interface = profile.interfaces['ns1::ns2::Interface']
        assert interface.name == 'ns1::ns2::Interface'
        accessor = interface.methods['DoTheThing(int)']
        assert accessor == Method(
            name='DoTheThing(int)',
            return_type='int',
            parameters=[Parameter(name='x', type='int')],
        )


class TestAnnotations:
    def test_simple_annotation(self):
        expected = Annotation('Serializable', {})
        assert parse_annotations('  // @IPC(Serializable)') == expected

    def test_annotation_with_kwarg(self):
        annotation = parse_annotations('  // @IPC(Serializable, auto=False)')
        expected = Annotation('Serializable', {'auto': False})
        assert annotation == expected

    def test_annotation_with_implied_boolean_kwarg(self):
        annotation = parse_annotations('  // @IPC(Serializable, auto)')
        expected = Annotation('Serializable', {'auto': True})
        assert annotation == expected

    def test_line_without_annotation(self):
        assert parse_annotations('  int foo = 1') is None

    def test_empty_line(self):
        assert parse_annotations('') is None

    def test_invalid_annotation(self):
        with pytest.raises(ValueError):
            parse_annotations('// @IPC(Invalid-Annotation)')


class TestFieldParse:
    def test_simple_field(self):
        fields = parse_fields('int foo')
        assert fields == [Field('foo', type_name='int')]

    def test_multiple_fields(self):
        fields = parse_fields('int foo, bar, baz')
        assert fields == [
            Field('foo', type_name='int'),
            Field('bar', type_name='int'),
            Field('baz', type_name='int'),
        ]

    def test_single_field_with_assignment_default(self):
        fields = parse_fields('int foo = 0')
        assert fields == [Field('foo', type_name='int')]

    def test_multiple_fields_with_assignment_default(self):
        fields = parse_fields('int foo = 0, bar = -1, baz = 100')
        assert fields == [
            Field('foo', type_name='int'),
            Field('bar', type_name='int'),
            Field('baz', type_name='int'),
        ]

    def test_single_field_with_initializer_default(self):
        fields = parse_fields('int foo{0}')
        assert fields == [Field('foo', type_name='int')]

    def test_single_field_with_parenthesis_default(self):
        fields = parse_fields('int foo(0)')
        assert fields == [Field('foo', type_name='int')]

    def test_multiple_fields_with_initializer_default(self):
        fields = parse_fields('int foo{0}, bar{-1}, baz{100}')
        assert fields == [
            Field('foo', type_name='int'),
            Field('bar', type_name='int'),
            Field('baz', type_name='int'),
        ]

    def test_templated_collection(self):
        fields = parse_fields('std::vector<std::uint32_t> collection = {}')
        assert fields == [
            Field('collection', type_name='std::vector<std::uint32_t>')
        ]

    def test_multiline_declaration(self):
        fields = parse_fields("""
        int
            a = 1,
            b = 2,
            c = 3;
        """)
        assert fields == [
            Field('a', type_name='int'),
            Field('b', type_name='int'),
            Field('c', type_name='int'),
        ]

    def test_namespaced_type(self):
        fields = parse_fields('std::size_t foo')
        assert fields == [Field('foo', type_name='std::size_t')]
