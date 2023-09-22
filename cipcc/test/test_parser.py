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
    Field,
    Annotation,
    InvalidAnnotation,
    NonExtendableMethodError,
    InvalidParamDeclaration,
    ReferenceParamError,
    InvalidParamTypeError,
    InvalidReturnTypeError,
    parse,
    parse_annotations,
    parse_fields,
    parse_methods,
    split_params,
    parse_param,
)
from ..interface import (
    Profile, Serializable, SerializableStruct, Method, Parameter
)
from .util import get_resource


class TestParser:
    """Contains Parser tests."""

    def test_simple_enum(self):
        header = get_resource('serializable/enum.h')
        profile = parse([header])
        mode = profile.serializable_types['Mode']
        assert mode.type == Serializable.Type.ENUM

    def test_enum_class(self):
        header = get_resource('serializable/enum_class.h')
        profile = parse([header])
        mode = profile.serializable_types['Mode']
        assert mode.type == Serializable.Type.ENUM

    def test_simple_struct(self):
        header = get_resource('serializable/struct.h')
        profile = parse([header])
        foo = profile.serializable_types['Foo']
        assert foo.type == Serializable.Type.STRUCT
        assert isinstance(foo, SerializableStruct)
        id_field = foo.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = foo.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'

    def test_simple_class(self):
        header = get_resource('serializable/class.h')
        profile = parse([header])
        foo = profile.serializable_types['Foo']
        assert foo.type == Serializable.Type.STRUCT
        assert isinstance(foo, SerializableStruct)
        id_field = foo.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = foo.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'

    def test_struct_aggregate(self):
        header = get_resource('serializable/struct_aggregate.h')
        profile = parse([header])
        foo = profile.serializable_types['Foo']
        assert foo.type == Serializable.Type.STRUCT
        assert isinstance(foo, SerializableStruct)
        for field_name in 'a', 'b', 'c':
            id_field = foo.fields[field_name]
            assert id_field.name == field_name
            assert id_field.type_name == 'std::int32_t'

    def test_struct_on_single_line(self):
        header = get_resource('serializable/struct_inline.h')
        profile = parse([header])
        foo = profile.serializable_types['Foo']
        assert foo.type == Serializable.Type.STRUCT
        assert isinstance(foo, SerializableStruct)
        id_field = foo.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = foo.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'

    def test_struct_with_multiline_declaration(self):
        header = get_resource('serializable/struct_multiline_decl.h')
        profile = parse([header])
        foo = profile.serializable_types['Foo']
        assert foo.type == Serializable.Type.STRUCT
        assert isinstance(foo, SerializableStruct)
        id_field = foo.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = foo.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'

    def test_struct_with_defaults(self):
        header = get_resource('serializable/struct_with_defaults.h')
        profile = parse([header])
        foo = profile.serializable_types['Foo']
        assert foo.type == Serializable.Type.STRUCT
        assert isinstance(foo, SerializableStruct)
        id_field = foo.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = foo.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'

    def test_class_with_methods(self):
        header = get_resource('serializable/class_with_methods.h')
        profile = parse([header])
        foo = profile.serializable_types['Foo']
        assert foo.type == Serializable.Type.STRUCT
        assert isinstance(foo, SerializableStruct)
        id_field = foo.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = foo.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'

    def test_namespaced_serializable(self):
        header = get_resource('serializable/namespaced_struct.h')
        profile = parse([header])
        foo = profile.serializable_types['bar::baz::Foo']
        assert isinstance(foo, SerializableStruct)
        assert foo.type == Serializable.Type.STRUCT
        id_field = foo.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = foo.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'

    def test_nested_serializable(self):
        header = get_resource('serializable/nested_struct.h')
        profile = parse([header])
        foo = profile.serializable_types['bar::Interface::Foo']
        assert foo.type == Serializable.Type.STRUCT
        assert isinstance(foo, SerializableStruct)
        id_field = foo.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = foo.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'

    def test_serializable_struct_in_struct(self):
        header = get_resource('serializable/struct_in_struct.h')
        profile = parse([header])
        a = profile.serializable_types['ns::A']
        assert a.type == Serializable.Type.STRUCT
        assert isinstance(a, SerializableStruct)
        id_field = a.fields['id']
        assert id_field.name == 'id'
        assert id_field.type_name == 'std::size_t'
        name_field = a.fields['name']
        assert name_field.name == 'name'
        assert name_field.type_name == 'std::string'
        b = profile.serializable_types['ns::B']
        assert b.type == Serializable.Type.STRUCT
        assert isinstance(b, SerializableStruct)
        a_field = b.fields['a']
        assert a_field.name == 'a'
        assert a_field.type_name == 'ns::A'

    def test_accessor_method(self):
        header = get_resource('method/accessor.h')
        profile = parse([header])
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
        profile = parse([header])
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
        profile = parse([header])
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
        profile = parse([header])
        interface = profile.interfaces['Interface']
        assert interface.name == 'Interface'
        accessor = interface.methods['Encode(int)const']
        assert accessor == Method(
            name='Encode(int)const',
            return_type='int',
            parameters=[Parameter(name='foo', type='int')],
        )

    def test_multiline_method(self):
        header = get_resource('method/multiline.h')
        profile = parse([header])
        interface = profile.interfaces['Interface']
        assert interface.name == 'Interface'
        accessor = interface.methods['Encode(int,int)const']
        assert accessor == Method(
            name='Encode(int,int)const',
            return_type='int',
            parameters=[
                Parameter(name='a', type='int'),
                Parameter(name='b', type='int'),
            ],
        )

    def test_optional_param_method(self):
        header = get_resource('method/optional_param.h')
        profile = parse([header])
        interface = profile.interfaces['Interface']
        assert interface.name == 'Interface'
        accessor_a = interface.methods['DoTheThing(int)']
        assert accessor_a == Method(
            name='DoTheThing(int)',
            return_type='int',
            parameters=[Parameter(name='foo', type='int')],
        )
        accessor_b = interface.methods['DoTheThing(int,int)']
        assert accessor_b == Method(
            name='DoTheThing(int,int)',
            return_type='int',
            parameters=[
                Parameter(name='foo', type='int'),
                Parameter(name='flags', type='int'),
            ],
        )

    def test_overloaded_method(self):
        header = get_resource('method/overloaded.h')
        profile = parse([header])
        interface = profile.interfaces['Interface']
        assert interface.name == 'Interface'
        assert interface.methods['Encode(std::string)const'] == Method(
            name='Encode(std::string)const',
            return_type='int',
            parameters=[Parameter(name='x', type='std::string')],
        )
        assert interface.methods['Encode(std::int32_t)const'] == Method(
            name='Encode(std::int32_t)const',
            return_type='int',
            parameters=[Parameter(name='x', type='std::int32_t')],
        )

    def test_unary_method(self):
        header = get_resource('method/unary.h')
        profile = parse([header])
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
        profile = parse([header])
        interface = profile.interfaces['ns1::ns2::Interface']
        assert interface.name == 'ns1::ns2::Interface'
        accessor = interface.methods['DoTheThing(int)']
        assert accessor == Method(
            name='DoTheThing(int)',
            return_type='int',
            parameters=[Parameter(name='x', type='int')],
        )

    def test_namespaced_serializable_type(self):
        header = get_resource('method/namespaced_type.h')
        profile = parse([header])
        interface = profile.interfaces['ns1::ns2::Interface']
        assert interface.name == 'ns1::ns2::Interface'
        init = interface.methods['Init(ns1::Conf)']
        assert init == Method(
            name='Init(ns1::Conf)',
            return_type='int',
            parameters=[
                Parameter(name='conf', type='ns1::Conf')
            ],
        )
        accessor = interface.methods['conf()const']
        assert accessor == Method(
            name='conf()const',
            return_type='ns1::Conf',
            parameters=[],
        )

    def test_nested_serializable_type(self):
        header = get_resource('method/nested_type.h')
        profile = parse([header])
        interface = profile.interfaces['ns1::ns2::Interface']
        assert interface.name == 'ns1::ns2::Interface'
        init = interface.methods['Init(ns1::ns2::Interface::Conf)']
        assert init == Method(
            name='Init(ns1::ns2::Interface::Conf)',
            return_type='int',
            parameters=[
                Parameter(name='conf', type='ns1::ns2::Interface::Conf')
            ],
        )
        accessor = interface.methods['conf()const']
        assert accessor == Method(
            name='conf()const',
            return_type='ns1::ns2::Interface::Conf',
            parameters=[],
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
        with pytest.raises(InvalidAnnotation):
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


class TestMethodParse:
    def test_unary_function(self):
        methods = parse_methods('virtual int foo(int x)')
        assert methods == [
            Method(
                'foo(int)',
                return_type='int',
                parameters=[Parameter('x', type='int')],
            ),
        ]

    def test_binary_function(self):
        methods = parse_methods('virtual int foo(std::string x, std::size_t y)')
        assert methods == [
            Method(
                'foo(std::string,std::size_t)',
                return_type='int',
                parameters=[
                    Parameter('x', type='std::string'),
                    Parameter('y', type='std::size_t'),
                ],
            ),
        ]

    def test_consumer(self):
        methods = parse_methods('virtual void foo(int x)')
        assert methods == [
            Method(
                'foo(int)',
                return_type='void',
                parameters=[Parameter('x', type='int')],
            ),
        ]

    def test_producer(self):
        methods = parse_methods('virtual std::string foo()')
        assert methods == [
            Method('foo()', return_type='std::string', parameters=[]),
        ]

    def test_unary_const_method(self):
        methods = parse_methods('virtual int foo(int x) const')
        assert methods == [
            Method(
                'foo(int)const',
                return_type='int',
                parameters=[Parameter('x', type='int')],
            ),
        ]

    def test_pure_virtual_method(self):
        methods = parse_methods('virtual int f() const = 0')
        assert methods == [
            Method('f()const', return_type='int', parameters=[]),
        ]

    def test_pure_virtual_method_with_tail_return(self):
        methods = parse_methods('virtual auto f() const -> int = 0')
        assert methods == [
            Method('f()const', return_type='int', parameters=[]),
        ]

    def test_function_with_attribute(self):
        methods = parse_methods('[[nodiscard]] virtual int foo(int x)')
        assert methods == [
            Method(
                'foo(int)',
                return_type='int',
                parameters=[Parameter('x', type='int')],
            ),
        ]

    def test_function_with_attribute_macro(self):
        methods = parse_methods(
            'LIBRARY_DEPRECATED("Don\'t use") virtual int foo(int x)'
        )
        assert methods == [
            Method(
                'foo(int)',
                return_type='int',
                parameters=[Parameter('x', type='int')],
            ),
        ]

    def test_function_with_default(self):
        methods = parse_methods('virtual int foo(int x = 0)')
        assert methods == [
            Method('foo()', return_type='int', parameters=[]),
            Method(
                'foo(int)',
                return_type='int',
                parameters=[Parameter('x', type='int')],
            ),
        ]

    def test_function_with_multiple_defaults(self):
        methods = parse_methods(
            'virtual int foo(int x = 0, std::string msg = "")'
        )
        assert methods == [
            Method('foo()', return_type='int', parameters=[]),
            Method(
                'foo(int)',
                return_type='int',
                parameters=[Parameter('x', type='int')],
            ),
            Method(
                'foo(int,std::string)',
                return_type='int',
                parameters=[
                    Parameter('x', type='int'),
                    Parameter('msg', type='std::string'),
                ],
            ),
        ]

    def test_function_with_struct_default(self):
        profile = Profile()
        profile.serializable_types['Conf'] = SerializableStruct(
            name='Conf', type='struct'
        )
        methods = parse_methods('virtual int foo(Conf conf = {})', profile)
        assert methods == [
            Method('foo()', return_type='int', parameters=[]),
            Method(
                'foo(Conf)',
                return_type='int',
                parameters=[Parameter('conf', type='Conf')],
            ),
        ]

    def test_non_virtual_function(self):
        with pytest.raises(NonExtendableMethodError):
            parse_methods('int foo(int x)')  # Cannot be overridden

    def test_final_function(self):
        with pytest.raises(NonExtendableMethodError):
            parse_methods('int foo(int x) final')  # Cannot be overridden

    def test_override_function(self):
        methods = parse_methods('int foo(int x) override')
        assert methods == [
            Method(
                'foo(int)',
                return_type='int',
                parameters=[Parameter('x', type='int')],
            ),
        ]

    @pytest.mark.parametrize(
        'signature, exception_type',
        [
            ('virtual int f(int x[3] = nullptr)', ReferenceParamError),
            ('virtual int f(const int* x = nullptr)', ReferenceParamError),
            ('virtual int f(long c)', InvalidParamTypeError),
            ('virtual int f(std::array<int32_t, 4> x)', InvalidParamTypeError),
            ('virtual long f(int x)', InvalidReturnTypeError),
        ]
    )
    def test_invalid_methods(self, signature, exception_type):
        with pytest.raises(exception_type):
            parse_methods(signature)


@pytest.mark.parametrize(
    'text, expected',
    [
        ('int x, int y', ['int x', 'int y']),
        ('Foo<int, int> data', ['Foo<int, int> data']),
        ('', []),
    ]
)
def test_parameter_splitting(text, expected):
    assert split_params(text) == expected


class TestParamParse:
    @pytest.mark.parametrize(
        'text, param_type, name, optional',
        [
            ('int x', 'int', 'x', False),
            ('int x = 10', 'int', 'x', True),
            ('std::size_t x = foo[1]', 'std::size_t', 'x', True),
            ('std::vector<int> x = {}', 'std::vector<int>', 'x', True),
            ('std::vector< int> x = {}', 'std::vector<int>', 'x', True),
            ('std::vector <int> x = {}', 'std::vector<int>', 'x', True),
            ('std::map<int, int> x = {}', 'std::map<int,int>', 'x', True),
            (
                'std::vector<std::vector<int>> x = {}',
                'std::vector<std::vector<int>>', 'x', True
            ),
            ('int x=10', 'int', 'x', True),
            ('std::string s = {}', 'std::string', 's', True),
            ('int foo = default()', 'int', 'foo', True),
            ('int foo = default ()', 'int', 'foo', True),
            ('const int& x', 'int const&', 'x', False),
            ('[[maybe_unused]] const int& x', 'int const&', 'x', False),
            ('LIB_UNUSED int const& x', 'int const&', 'x', False),
        ]
    )
    def test_parameter_parsing(self, text, param_type, name, optional):
        param = parse_param(text)
        results = param.name, str(param.type), param.optional
        assert results == (name, param_type, optional)

    @pytest.mark.parametrize(
        'text',
        [
            'const int* foo = nullptr',
            'const int *foo = nullptr',
            'const int* const* x = nullptr',
            'int*** x',
            'const int* foo',
            'const int foo',  # Unexpected const qualification
            'std::string& conf',
            'std::string &conf',
            'const int arr[]',
            'const int arr []',
            'const int arr[] = {}',
            'const std::vector<std::size_t>* result',
            'std::vector<int*> pointers',
        ]
    )
    def test_reference_param_detection(self, text):
        with pytest.raises(ReferenceParamError):
            parse_param(text)

    @pytest.mark.parametrize(
        'text',
        [
            'int (*x)(double)',
            'int (*(*x)(double))[3] = nullptr',
        ]
    )
    def test_function_pointer_param(self, text):
        """
        Test C function pointer params raise some form of param error.

        C-style function pointer parameters are both hard to parse and
        unsupported, so as long as some form of error is produced, there
        is not much reason to attempt to parse these.
        """
        with pytest.raises(InvalidParamDeclaration):
            parse_param(text)

    @pytest.mark.parametrize(
        'text',
        [
            'long x',
            'const short x = 0',
            'char c',
            'std::array<std::int32_t, 4> arr',
        ]
    )
    def test_unsupported_parameter_types(self, text):
        """
        Tests that parameters with unsupported types are detected.
        """
        with pytest.raises(InvalidParamTypeError):
            parse_param(text)

    @pytest.mark.parametrize(
        'text',
        [
            'invalid x',
            'std::invalid x',
            'std::vector<invalid> x',
            'std::vector<std::vector<invalid>> x',
            'std::map<invalid, int> x',
            'std::map<int, invalid> x',
        ]
    )
    def test_invalid_types(self, text):
        """
        Tests that parameters with invalid type names are detected.
        """
        with pytest.raises(InvalidParamTypeError):
            parse_param(text)
