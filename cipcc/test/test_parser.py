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
from ..interface import Serializable
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
