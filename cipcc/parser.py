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
Module containing interface parser.
"""
import ast
import contextlib
from dataclasses import dataclass
import enum
import functools
import itertools
from pathlib import Path
import re
import typing as ty

from .interface import (
    Profile,
    Serializable,
    SerializableStruct,
    Field,
    Interface,
    Method,
    Callback,
    Parameter,
)


#######################################################################
# Parsing Exceptions


class ParsingError(RuntimeError):
    """Exception raised when invalid input code is received."""

    def __init__(self, state: 'CodeState', msg: str) -> None:
        super().__init__(f'On line {state.line_no}, col: {state.col_no}: {msg}')


class InvalidFieldDeclaration(ValueError):
    """
    Exception produced when parse_fields() is given an
    invalid declaration.
    """


class InvalidMethodDeclaration(ValueError):
    """
    Exception raised when parse_methods() is given an
    invalid declaration.
    """


class NonExtendableMethodError(InvalidMethodDeclaration):
    """
    Exception raised when an interface method cannot be overridden.

    This defeats the purpose of an interface, and is therefore an error.
    """


class InvalidParamDeclaration(InvalidMethodDeclaration):
    """
    Exception raised when a parameter declaration is invalid.
    """


class ReferenceParamError(InvalidParamDeclaration):
    """
    Exception raised when a parameter references external memory.

    References, whether in the form of pointers, references, or array
    references, cannot be serialized reliably, and so are disallowed.
    """


class InvalidTypeError(ValueError):
    """
    Base type for invalid type errors.

    See InvalidParamTypeError and InvalidReturnTypeError.
    """


class InvalidParamTypeError(InvalidParamDeclaration, InvalidTypeError):
    """
    Exception raised when a parameter type is unsupported.
    """


class InvalidReturnTypeError(InvalidMethodDeclaration, InvalidTypeError):
    """
    Exception raised when a return type is unsupported.
    """


class InvalidAnnotation(ValueError):
    """
    Exception raised when an annotation with invalid format
    is encountered.
    """


class IncludeResolutionError(KeyError):
    """
    Exception raised when an include cannot be resolved.
    """


class CircularIncludeError(RuntimeError):
    """
    Exception produced when headers appear to include each other.
    """


#######################################################################
# Basic parsing types.

_BUILTIN_TYPE_NAMES = [
    'int',
    'float',
    'double',
    'size_t',
    'std::size_t',
    'std::string',
    'std::deque',
    'std::list',
    'std::vector',
    'std::map',
    'std::unordered_map',
]


def _get_builtin_types():
    # Add int(N)_t and variations to builtin types.
    types = {}
    for bit_size, sign_prefix, namespace in itertools.product(
            ('8', '16', '32', '64'),
            ('u', ''),
            ('std::', ''),
    ):
        types[f'{namespace}{sign_prefix}int{bit_size}_t'] = Serializable(
            f'std::{sign_prefix}int{bit_size}_t',
            type=Serializable.Type.BUILTIN,
        )
    for builtin_name in _BUILTIN_TYPE_NAMES:
        types[builtin_name] = Serializable(
            builtin_name, type=Serializable.Type.BUILTIN
        )
    return types


BUILTIN_TYPES = _get_builtin_types()

UNSUPPORTED_INTS = {
    'char',
    'long',
    'short',
}

UNIMPLEMENTED_COLLECTIONS = {
    'std::array',
    'std::forward_list',
    'std::stack',
    'std::queue',
    'std::priority_queue',
    'std::flat_set',
    'std::flat_map',
    'std::flat_multiset',
    'std::flat_multimap',
}


@dataclass
class CodeState:
    """
    Data object containing the current state of the code being parsed.
    """
    index: int
    line_no: int
    col_no: int
    source_name: str
    comment_start: str
    escape: bool
    quoting: ty.Dict[str, bool]
    brace_depth: ty.Dict[str, int]
    brace_stack: ty.List[str]
    statement_braces: ty.List[str]
    line: str
    commented_line: str
    scope_text: ty.List[str]
    observers: ty.List['CodeObserver']

    @property
    def is_quoted(self):
        return any(self.quoting.values())

    @property
    def is_commented(self):
        return bool(self.comment_start)

    @property
    def scope_index(self) -> int:
        return len(self.scope_text) - 1

    def add_observer(self, observer: 'CodeObserver') -> None:
        self.observers.append(observer)

    def remove_observer(self, observer: 'CodeObserver') -> None:
        self.observers.remove(observer)

    def notify(self, event: 'CodeEvent') -> None:
        for observer in self.observers:
            if observer.events & event:
                observer(event, self)

    def scope_statement(self, scope_index: int = -1):
        scope_text = self.scope_text[scope_index]
        return scope_text[scope_text.rfind(';') + 1:]

    @property
    def statement(self) -> str:
        return self.scope_statement()

    @property
    def scope_prefix(self) -> str:
        """
        Gets statement preceding current scope.

        This is useful for retrieving the declaration preceding a
        namespace, class, or other type when an opening bracket
        is encountered.

        The returned text is likely to contain significant unexpected
        text at the beginning, due to functions or other code constructs
        which precede the declaration of interest. It is up to the
        consumer of the returned prefix to handle this.
        """
        assert self.scope_index > 0
        return self.scope_statement(-2)


class CodeEvent(enum.IntEnum):
    """
    Enum indicating an event which has occurred while parsing code.
    """
    LINE_END = 0x01
    QUOTE_START = 0x02
    QUOTE_END = 0x04
    BRACKET_START = 0x10
    BRACKET_END = 0x20
    STATEMENT_END = 0x40
    END_OF_FILE = 0x80


class CodeObserver:
    """
    Object which is notified when a code event occurs.
    """
    def __init__(
            self,
            fn: ty.Callable[['CodeEvent', 'CodeState'], None],
            events: int = 0,
    ) -> None:
        self.fn = fn
        self.events = events

    def __call__(self, event: 'CodeEvent', state: 'CodeState') -> None:
        assert event & self.events
        self.fn(event, state)


def code_walk(
        text: str, source_name: str, observers: ty.Iterable[CodeObserver]
) -> None:
    """
    Walks across a file, invoking observers when events occur.

    Observers are passed line ends, code blocks, quotes, and other
    events, and may either perform actions directly, or add additional
    code observers to handle specialized cases: Serializable types,
    Interface definitions, etc.

    Note that this does _not_ attempt to parse all possible syntax
    supported by the C++ language. It is intended to be capable enough
    to handle the subsets required by the CIPC library, and
    nothing more.

    :param text: Text to iterate over.
    :param source_name: Name of source file or input being walked.
    :param observers: Initial CodeObservers to give parsing events.
    These observers may in turn add additional observers when
    events occur.
    :return: None
    """
    state = CodeState(
        index=0,
        line_no=1,  # Files tend to be shown 1-indexed in most editors.
        col_no=1,
        source_name=source_name,
        comment_start='',
        escape=False,
        quoting={'"': False, "'": False},
        brace_depth={brace_pair[0]: 0 for brace_pair in BRACE_PAIRS},
        brace_stack=[],
        statement_braces=[],
        commented_line='',
        line='',
        scope_text=[''],
        observers=list(observers),
    )

    while state.index < len(text):
        char = text[state.index]
        initial_scope = state.scope_index
        initial_line = state.line_no
        deferred_event = 0

        # Handle comments.
        if not state.is_quoted:
            if char in '/*' and state.commented_line.endswith('/'):  # Start
                state.comment_start = '/' + char
                state.line = state.line[:-1]
                state.scope_text[state.scope_index] = \
                    state.scope_text[state.scope_index][:-1]
            elif all((
                state.comment_start == '/*',
                char == '/',
                state.commented_line.endswith('*')
            )):  # End
                state.comment_start = ''
        if char != '\n':
            state.commented_line += char

        # Handle code constructs.
        if char == '\n':
            state.notify(CodeEvent.LINE_END)
            state.line = ''
            state.commented_line = ''
            state.line_no += 1
            state.col_no = 0
            if state.comment_start == '//':
                state.comment_start = ''
        elif state.is_quoted:
            if state.escape:
                state.escape = False
            else:
                if char == '\\':
                    state.escape = True
                elif char in '"\'' and state.quoting[char]:
                    state.quoting[char] = False
                    state.notify(CodeEvent.QUOTE_END)
                    state.scope_text.pop()
        elif not state.is_commented:
            if char in '"\'':  # Begin quote.
                state.quoting[char] = True
                state.scope_text.append('')
                deferred_event = CodeEvent.QUOTE_START
            elif char in BRACE_START_CHARS:  # Begin block.
                state.brace_depth[char] += 1
                state.brace_stack.append(char)
                state.scope_text.append('')
                deferred_event = CodeEvent.BRACKET_START
            elif char in BRACE_END_CHARS:  # End block.
                matching_brace = _paired_brace(char)
                if not state.brace_stack:
                    raise ParsingError(
                        state,
                        f'Unexpected closing brace {repr(char)} found.'
                    )
                if state.brace_stack[-1] != matching_brace:
                    expected_brace = _paired_brace(state.brace_stack[-1])
                    raise ParsingError(
                        state,
                        f'Unexpected closing brace {repr(char)} found. '
                        f'Expected: {repr(expected_brace)}.'
                    )
                state.notify(CodeEvent.BRACKET_END)
                state.brace_depth[matching_brace] -= 1
                state.brace_stack.pop()
                state.scope_text.pop()
            elif char == ';':
                # Handle statement end.
                # Note that this does not handle control flow blocks,
                # however it is sufficient for cipc's uses.
                state.notify(CodeEvent.STATEMENT_END)

        # Common bookkeeping.
        state.index += 1
        if not state.is_commented:
            state.scope_text[min(initial_scope, state.scope_index)] += char
        if state.line_no == initial_line:
            state.col_no += 1
            state.line += char
        if deferred_event:
            state.notify(deferred_event)
    state.notify(CodeEvent.END_OF_FILE)


def parse(
        headers: ty.Iterable[Path], include_dirs: ty.Iterable[Path] = ()
) -> Profile:
    """
    Parses set of interface files, and produces an
    interface Profile.

    :param headers: Interface headers to parse.
    :param include_dirs: Directories in which to search for includes.
    :return: Profile containing parsed interfaces.
    """
    profile = Profile()
    namespace_observer = NamespaceObserver()

    def watch_for_root_annotations(_, state: 'CodeState') -> None:
        annotation = parse_annotations(state.line)
        if not annotation:
            return
        kwargs = annotation.kwargs
        namespace = namespace_observer.namespace
        if annotation.key == 'Serializable':
            state.add_observer(SerializableCodeObserver(
                profile, namespace, **kwargs
            ))
        elif annotation.key == 'Interface':
            state.add_observer(InterfaceCodeObserver(profile, namespace))

    for header in explore_includes(headers, include_dirs):
        if header.is_dir():
            raise ValueError(
                f'Passed path: {header} is a directory, not a header.'
            )
        text = header.read_text()
        root_observer = CodeObserver(
            watch_for_root_annotations, events=CodeEvent.LINE_END
        )
        code_walk(text, header.name, [root_observer, namespace_observer])

    return profile


#######################################################################
# Code observer definitions.


class NamespaceObserver(CodeObserver):
    """
    Tracks namespace changes.

    The current namespace is made available via the .namespace attribute.
    """
    DECLARATION_PATTERN = re.compile(r'namespace\s+(?P<name>[\w:]+)\s?{$')

    class NamespaceLayer(ty.NamedTuple):
        name: str  # Name. May contain combined namespaces (Ex: 'a::b')
        brace_stack: ty.List[str]  # Brace stack at declaration site.

    def __init__(self) -> None:
        handled_events = CodeEvent.BRACKET_START | CodeEvent.BRACKET_END
        super().__init__(self.__call__, handled_events)
        self.namespaces: ty.List[NamespaceObserver.NamespaceLayer] = []

    def __call__(self, event: 'CodeEvent', state: 'CodeState') -> None:
        """Handles namespace start or end."""
        if event == CodeEvent.BRACKET_START and state.brace_stack[-1] == '{':
            for pattern in (
                    self.DECLARATION_PATTERN,
                    SerializableCodeObserver.DECLARATION_PATTERN
            ):
                if match := pattern.search(state.scope_prefix):
                    self.namespaces.append(self.NamespaceLayer(
                        name=match['name'], brace_stack=state.brace_stack.copy()
                    ))
                    break

        elif (
                event == CodeEvent.BRACKET_END and
                state.brace_stack[-1] == '{' and
                self.namespaces and
                state.brace_stack == self.namespaces[-1].brace_stack
        ):
            self.namespaces.pop()

    @property
    def namespace(self) -> str:
        return '::'.join(layer.name for layer in self.namespaces)


class SerializableCodeObserver(CodeObserver):
    """Handles serializable type declarations."""

    DECLARATION_PATTERN = re.compile(
        r'(?P<type>struct|class|enum)\s+(?:\S+\s+)*(?P<name>\w+)\s*{$'
    )

    def __init__(
            self, profile: Profile, namespace: str, auto: bool = True
    ) -> None:
        """
        Initializes SerializableCodeObserver.

        :param profile: Profile to add parsed Serializable to.
        """
        super().__init__(self.__call__, CodeEvent.BRACKET_START)
        self.namespace = namespace
        self.auto = auto
        self.name = None
        self.scope_brace_stack = []
        self.profile = profile
        self.serializable = None
        self.field_observer = None

    def __call__(self, event: 'CodeEvent', state: 'CodeState') -> None:
        if event == CodeEvent.BRACKET_START:
            declaration = state.scope_prefix
            match = self.DECLARATION_PATTERN.search(declaration)
            if not match:
                prefix_text = remove_prefix(r'(?.*})\s*', declaration)
                raise ParsingError(
                    state,
                    'Serializable type had unrecognized declaration: '
                    f'{repr(prefix_text)}.'
                )
            self.name = '::'.join((self.namespace, match['name'])) \
                if self.namespace else match['name']
            self.type = {
                'struct': Serializable.Type.STRUCT,
                'class': Serializable.Type.STRUCT,
                'enum': Serializable.Type.ENUM,
            }[match['type']]
            self.scope_brace_stack = state.brace_stack.copy()
            if self.name in self.profile.serializable_types:
                raise ParsingError(
                    state,
                    f'Serializable with name: {self.name} already exists in '
                    f'profile.'
                )
            if self.type == Serializable.Type.STRUCT:
                self.serializable = SerializableStruct(self.name, self.type)
                if self.auto:
                    self.field_observer = AutoFieldCodeObserver(self)
                else:
                    self.field_observer = ExplicitFieldCodeObserver(self)
                state.add_observer(self.field_observer)
            else:
                self.serializable = Serializable(self.name, self.type)
            self.profile.serializable_types[self.name] = self.serializable
            self.events = CodeEvent.BRACKET_END
        elif event == CodeEvent.BRACKET_END:
            if state.brace_stack == self.scope_brace_stack:
                state.remove_observer(self)
                if self.field_observer:
                    state.remove_observer(self.field_observer)

    @property
    def inner_ns(self) -> str:
        return '::'.join((self.namespace, self.name))


class AutoFieldCodeObserver(CodeObserver):
    """
    Code observer handling field definitions.

    This observer runs until the struct it is handling is closed, at
    which point it will be removed by the SerializableCodeObserver which
    added it.

    This field code observer attempts to add all fields to the
    serialized object.
    """
    def __init__(
            self, serializable_observer: 'SerializableCodeObserver'
    ) -> None:
        super().__init__(self.__call__, events=CodeEvent.STATEMENT_END)
        self.serializable_observer = serializable_observer

    def __call__(self, event: 'CodeEvent', state: 'CodeState') -> None:
        if state.brace_stack != self.serializable_observer.scope_brace_stack:
            return

        profile = self.serializable_observer.profile
        inner_ns = self.serializable_observer.inner_ns
        try:
            for field in parse_fields(state.statement, profile, inner_ns):
                fields = self.serializable_observer.serializable.fields
                if field.name in fields:
                    raise ParsingError(
                        state,
                        f'Field {repr(field.name)} duplicates an earlier field '
                        'with the same name.'
                    )
                fields[field.name] = field
        except InvalidFieldDeclaration as declaration_err:
            raise ParsingError(state, str(declaration_err)) from declaration_err


class ExplicitFieldCodeObserver(CodeObserver):
    """
    Code observer handling field definitions.

    This observer runs until the struct it is handling is closed, at
    which point it will be removed by the SerializableCodeObserver which
    added it.

    Unlike AutoFieldCodeObserver, only manually annotated fields will
    be added to the serialized object.
    """
    def __init__(
            self, serializable_observer: 'SerializableCodeObserver'
    ) -> None:
        super().__init__(
            self.__call__,
            events=CodeEvent.LINE_END | CodeEvent.STATEMENT_END
        )
        self.serializable_observer = serializable_observer
        self.field_prefix = None

    def __call__(self, event: 'CodeEvent', state: 'CodeState') -> None:
        if state.brace_stack != self.serializable_observer.scope_brace_stack:
            return

        if event == CodeEvent.LINE_END:
            annotation = parse_annotations(state.line)
            if not annotation or annotation.key != 'Field':
                return
            self.field_prefix = state.statement

        elif event == CodeEvent.STATEMENT_END and self.field_prefix is not None:
            assert state.statement.startswith(self.field_prefix)
            statement = state.statement[len(self.field_prefix):]
            profile = self.serializable_observer.profile
            inner_ns = self.serializable_observer.inner_ns
            try:
                for field in parse_fields(statement, profile, inner_ns):
                    fields = self.serializable_observer.serializable.fields
                    if field.name in fields:
                        raise ParsingError(
                            state,
                            f'Field {repr(field.name)} duplicates an earlier '
                            'field with the same name.'
                        )
                    fields[field.name] = field
            except InvalidFieldDeclaration as declaration_err:
                raise ParsingError(
                    state, str(declaration_err)
                ) from declaration_err
            self.field_prefix = None


class InterfaceCodeObserver(CodeObserver):
    """Handles interface definitions."""

    DECLARATION_PATTERN = re.compile(
        r'(?P<type>struct|class)\s+(?:\S+\s+)*(?P<name>\w+)\s*{$'
    )

    def __init__(self, profile: Profile, namespace: str) -> None:
        super().__init__(self.__call__, CodeEvent.BRACKET_START)
        self.namespace = namespace
        self.name = None
        self.scope_brace_stack = []
        self.profile = profile
        self.interface = None
        self.method_observer = None

    def __call__(self, event: 'CodeEvent', state: 'CodeState') -> None:
        if event == CodeEvent.BRACKET_START:
            declaration = state.scope_prefix
            match = self.DECLARATION_PATTERN.search(declaration)
            if not match:
                prefix_text = remove_prefix(r'(?.*})\s*', declaration)
                raise ParsingError(
                    state,
                    'Interface had unrecognized declaration: '
                    f'{repr(prefix_text)}.'
                )
            if match['type'] == 'struct':
                raise ParsingError(
                    state,
                    "Interface declared as a 'struct' rather than as a class. "
                    'This may cause issues with certain compilers (msvc). '
                    'Use a class instead.'
                )
            self.name = '::'.join((self.namespace, match['name'])) \
                if self.namespace else match['name']
            self.scope_brace_stack = state.brace_stack.copy()
            if self.name in self.profile.serializable_types:
                raise ParsingError(
                    state,
                    f'Serializable with same name: {self.name} already exists '
                    'in profile.'
                )
            if self.name in self.profile.interfaces:
                raise ParsingError(
                    state,
                    f'Interface with same name {self.name} already exists '
                    'in profile.'
                )
            self.interface = Interface(self.name)
            self.method_observer = MethodCodeObserver(self)
            self.profile.interfaces[self.name] = self.interface
            self.events = CodeEvent.BRACKET_END
            state.add_observer(self.method_observer)
        elif event == CodeEvent.BRACKET_END and \
                state.brace_stack == self.scope_brace_stack:
            state.remove_observer(self)
            state.remove_observer(self.method_observer)


class MethodCodeObserver(CodeObserver):
    """
    Code observer handling interface method definitions.

    This observer will be instantiated and eventually removed by the
    InterfaceCodeObserver, at the beginning and end respectively
    of an interface class.
    """
    def __init__(self, interface_observer: 'InterfaceCodeObserver') -> None:
        super().__init__(self.__call__, events=CodeEvent.LINE_END)
        self.interface_observer = interface_observer
        self.ignored_method_prefix = None  # Set once annotation is found.
        self.declaration = None  # Appended to while parsing.
        self.annotation_line_no = None

    def __call__(self, event: 'CodeEvent', state: 'CodeState') -> None:
        """Handle code events produced while parsing an interface"""

        # Handle method annotation.
        if event == CodeEvent.LINE_END and \
                state.brace_stack == self.interface_brace_stack:
            self._handle_line_end(state)

        # Handle text from within method parameter list.
        # This would normally be ignored as it is in an inner scope, but
        # it must be parsed to obtain the function parameters.
        elif all((
                event == CodeEvent.BRACKET_START,
                state.brace_stack == self.interface_brace_stack + ['('],
        )):
            self._handle_round_bracket_open(state)
        elif all((
                event == CodeEvent.BRACKET_END,
                state.brace_stack == self.interface_brace_stack + ['('],
        )):
            self._handle_round_bracket_close(state)

        # Handle end of function declaration with or without body.
        elif all((
                event == CodeEvent.STATEMENT_END,
                self.ignored_method_prefix is not None,
                state.brace_stack == self.interface_brace_stack
        )) or all((
                event == CodeEvent.BRACKET_START,
                state.brace_stack == self.interface_brace_stack + ['{'],
        )):
            self._handle_signature_end(state)

    def _handle_line_end(self, state: 'CodeState') -> None:
        if self.declaration is not None:
            raise ParsingError(
                state,
                f'Annotation found while still parsing previous Method'
                f'annotation on line {self.annotation_line_no}.'
            )
        annotation = parse_annotations(state.line)
        if not annotation or annotation.key != 'Method':
            return
        self.ignored_method_prefix = state.statement
        self.annotation_line_no = state.line_no
        self.events |= (
                CodeEvent.BRACKET_START |
                CodeEvent.BRACKET_END |
                CodeEvent.STATEMENT_END
        )
        self.declaration = ''

    def _handle_round_bracket_open(self, state: 'CodeState') -> None:
        assert state.scope_prefix.startswith(self.ignored_method_prefix)
        appended_text = state.scope_prefix[self.ignored_len:]
        self.declaration += appended_text
        self.ignored_method_prefix += appended_text

    def _handle_round_bracket_close(self, state: 'CodeState') -> None:
        self.declaration += state.statement

    def _handle_signature_end(self, state: 'CodeState') -> None:
        signature_statement = state.statement if \
            state.brace_stack == self.interface_brace_stack else \
            state.scope_prefix
        assert signature_statement.startswith(self.ignored_method_prefix)
        self.declaration += signature_statement[self.ignored_len:]
        self.declaration = self.declaration.rstrip('{').strip()
        profile = self.interface_observer.profile
        ns = self.interface_observer.name
        try:
            signatures = parse_methods(self.declaration, profile, ns)
            interface = self.interface_observer.interface
            for signature in signatures:
                interface.methods[signature.name] = signature
        except InvalidMethodDeclaration as declaration_err:
            raise ParsingError(
                state, str(declaration_err)
            ) from declaration_err
        self.ignored_method_prefix = None  # Reset.
        self.declaration = None  # Reset
        self.annotation_line_no = None  # Reset
        self.events = CodeEvent.LINE_END  # Reset

    @property
    def interface_brace_stack(self) -> ty.List[str]:
        return self.interface_observer.scope_brace_stack

    @property
    def ignored_len(self) -> int:
        return len(self.ignored_method_prefix)


#######################################################################
# Parsing utilities


ANNOTATION_PATTERN = re.compile(r'@IPC\((.*)\)')
ANNOTATION_CONTENT = re.compile(
    r'\s*([a-zA-Z]+)\s*'
    r'((?:,\s*[a-zA-Z][a-zA-Z0-9]*(?:\s*=\s*?[a-zA-Z0-9]+)?)*)'
)
KEY_VALUE_PATTERN = re.compile(
    r'([a-zA-Z][a-zA-Z0-9]*)(?:\s*=\s*([a-zA-Z0-9]+))?'
)


class Annotation(ty.NamedTuple):
    key: str
    kwargs: ty.Dict[str, ty.Any]


def explore_includes(
        headers: ty.Iterable[Path], include_dirs: ty.Iterable[Path]
) -> ty.List[Path]:
    """
    Explores the passed header files for their recursive includes.

    #includes are followed until all headers which are included are
    discovered. All headers (including those passed) are then sorted
    based on their dependency order, with headers that include others
    appearing after the files they include.

    Headers which do not occur in one of the passed include directories
    (excepting the explicitly passed headers) will not be parsed.

    :param headers: Header files to read for #includes.
    :param include_dirs: Directories in which to look for includes.
    :return: Header paths in the order in which they should be parsed.
    """
    # Collection of include lists by the file which includes them.
    # All paths are normalized to their absolute path.
    parsed_files: ty.Dict[Path, ty.Set[Path]] = {}
    unparsed_files: ty.List[Path] = [header.resolve() for header in headers]

    while unparsed_files:
        header = unparsed_files.pop()
        if header in parsed_files:
            continue

        # Determine header includes.
        raw_includes = read_header_includes(header)
        includes = set()
        for include in raw_includes:
            with contextlib.suppress(KeyError):
                includes.add(resolve_include(include, include_dirs))
        parsed_files[header] = includes

        # Queue dependencies for parsing.
        for include in includes:
            if include not in parsed_files:
                unparsed_files.append(include)

    return find_parse_order(parsed_files)


INCLUDE_PATTERN = re.compile(rb'^ *# *include *(?P<include>"[^"]+"|<[^>]+>)')


def read_header_includes(header: Path) -> ty.List[str]:
    """
    Reads all includes which occur in a file.

    :param header: Path to file to parse.
    :return: List of included strings, including surrounding brackets
    or quote chars. Ex: ['<string>', '"foo.h"', '"baz.h"'].
    """
    includes = []
    with header.open('rb') as file:
        for line in file:
            match = INCLUDE_PATTERN.match(line)
            if match:
                includes.append(match['include'].decode('ascii'))
    return includes


def resolve_include(include: str, include_dirs: ty.Iterable[Path]) -> Path:
    """
    Resolves an included file name to a
    :param include: Raw include str (Ex: '<foo>' or '"foo.h"').
    :param include_dirs: Include dirs in which to look for a
    matching header.
    :return: Absolute, resolved path.
    :raises: IncludeResolutionError if file cannot be found.
    """
    # Strip quotes or brackets.
    if include.startswith('<'):
        assert include.endswith('>')
    elif include.startswith('"'):
        assert include.endswith('"')
    else:
        raise AssertionError(f'Bad include str: {include!r}')
    include = include[1:-1]

    # Look for file.
    for include_dir in include_dirs:
        checked_path = include_dir / include
        if checked_path.exists():
            return checked_path
    raise IncludeResolutionError(f'Cannot resolve {include!r}')


def find_parse_order(include_map: ty.Dict[Path, ty.Set[Path]]) -> ty.List[Path]:
    """
    Finds order in which to parse headers.

    Given a map of header files to their included direct dependencies,
    this function produces the order in which the headers should be
    parsed so that each header is parsed after its included files.

    :param include_map: Dict of headers to their direct dependencies.
    :return: List of headers in the order they should be parsed.
    """
    unsorted_headers = set(include_map.keys())

    # Check all includes match a known header.
    for header, includes in include_map.items():
        unknown_includes = includes - unsorted_headers
        assert not unknown_includes

    sorted_headers = set()
    ordering = []
    while unsorted_headers:
        made_progress = False
        for header in unsorted_headers:
            dependencies = include_map[header]
            if dependencies <= sorted_headers:
                ordering.append(header)
                sorted_headers.add(header)
                made_progress = True
        if not made_progress:
            raise CircularIncludeError(
                f'The following headers appear to form one or more circular '
                f'include chains: {unsorted_headers}'
            )
        unsorted_headers -= sorted_headers
    return ordering


def parse_annotations(line: str) -> ty.Optional[Annotation]:
    """
    Parses IPC annotations on a line into usable values.
    :param line:
    :return: Annotation type string, and kwargs.
    """
    match = ANNOTATION_PATTERN.search(line)
    if not match:
        return None
    match = ANNOTATION_CONTENT.fullmatch(match[1])
    if not match:
        raise InvalidAnnotation(f'Encountered invalid annotation: {repr(line)}')
    primary_key = match[1]
    kwarg_string = match[2]
    kwargs = {}
    for kwarg_string in kwarg_string.split(','):
        match = KEY_VALUE_PATTERN.search(kwarg_string)
        if not match:
            continue
        key, value = match.groups()
        kwargs[key] = ast.literal_eval(value) if value else True
    return Annotation(primary_key, kwargs)


LABEL_REGEX = re.compile(r'^\s+(?P<label>\w+):\s')
FIELD_TYPE_NAME_PATTERN = re.compile(
    r'(?P<type>(?P<cv>const\s+)?(?P<base_type>[\w:]+)'
    r'(?:\s*<(?P<tparam>[\w:<>,*&\s]*)>)?'
    r'(?P<type_suffix>(?:(?:const)?(?:\*|&|\s)+\s*)*))'
    r'(?<=[\s*&])(?P<name>\w+)\s*'
    r'(?P<array>(?:\[.*?])*)\s*',
    flags=re.DOTALL
)
FIELD_NAME_PATTERN = re.compile(r'^\s*(?P<name>\w+)')


def parse_fields(
        text: str, profile: Profile = Profile(), ns: str = ''
) -> ty.List['Field']:
    """
    Parse fields from field declaration statement.

    :param text: Declaration text (Ex: 'int foo = 1, baz = 2')
    :param profile: Profile containing types usable in fields.
    :param ns: Namespace containing fields being parsed.
    :return: List of fields parsed from declaration.
    """
    # Split preceding label (Ex: 'public:')
    match = LABEL_REGEX.match(text)
    if match:
        text = text[len(match.group()):]

    # Parse type_name.
    parts = text.split(',')
    match = FIELD_TYPE_NAME_PATTERN.search(parts[0])
    if not match:
        raise InvalidFieldDeclaration(
            f'Invalid or unrecognized field declaration: {repr(text.strip())}. '
            'Ensure a cipc-supported type is being used. '
            'See the Serializable types docs.'
        )
    try:
        type_name = resolve_type(match['base_type'].strip(), profile, ns).name
        tparams = [
            parse_param(tparam.strip() + ' x', profile, ns).type
            for tparam in split_params(match['tparam'] or [])
        ]
    except InvalidTypeError as type_error:
        raise InvalidFieldDeclaration(str(type_error)) from type_error
    type_name += '<' + ','.join(tparams) + '>' if tparams else ''

    fields = [Field(match['name'], type_name)]
    if len(parts) > 1:
        names = [FIELD_NAME_PATTERN.match(part)['name'] for part in parts[1:]]
        if any(
                complex_char in text_fragment for complex_char, text_fragment in
                itertools.product('*&[]', [type_name] + names)
        ):
            raise InvalidFieldDeclaration(
                'Complex field declarations should be on their own line. '
                'Avoid combining declarations of pointer, reference, or '
                f'array variables. Got declaration: {text}'
            )
        for name in names:
            fields.append(Field(name, type_name))

    return fields


METHOD_SIGNATURE_PATTERN = re.compile(
    r'(?:(?P<virtual>virtual)\s+)?'
    r'(?P<return>[\w:]+)\s+'
    r'(?P<name>\w+)\s*'
    r'\((?P<params>.*)\)\s*'
    r'(?P<cv>const)?\s*'
    r'(?P<ref>override|final)?\s*'
    r'(?:[\w\[\]()]+\s+)*'  # modifiers and attributes
    r'(?:->\s*(?P<tail_return>[\w:]+))?\s*'
    r'(?P<pure>=\s*0)?$',
    flags=re.DOTALL,
)
COLLAPSED_PARAM_PATTERNS = [
    (re.compile(r'\{.*}', flags=re.DOTALL), '{}'),
    (re.compile(r'\(.*\)', flags=re.DOTALL), '()'),
]
PARAM_PATTERN = re.compile(
    r'(?P<type>(?P<cv>const\s+)?(?P<base_type>[\w:]+)'
    r'(?:\s*<(?P<tparam>[\w:<>,*&\s]*)>)?'
    r'(?P<type_suffix>(?:(?:const)?(?:\*|&|\s)+\s*)*))'
    r'(?<=[\s*&])(?P<name>\w+)\s*'
    r'(?P<array>(?:\[.*?])*)\s*'
    r'(?:=\s*(?P<default>[\w:()\[\]{}"\s]+?))?\s*$',
    flags=re.DOTALL
)


class ParsedParam(ty.NamedTuple):
    """
    Tuple storing parameter info parsed from function signature.

    This type is used to convey the results of the parse_method()
    function, after which the information is moved to Parameter objects
    which will be stored in the produced Profile.
    """
    name: str
    type: str
    optional: bool


def parse_methods(
        text: str, profile: Profile = Profile(), ns: str = ''
) -> ty.List['Method']:
    """
    Parses method signatures from a method declaration.

    Multiple method signatures may be returned if default parameters
    are present in the parsed signature, which result in multiple
    overloaded definitions.

    :param text: Method declaration to parse.
    :param profile: Profile containing types usable in methods.
    :param ns: Namespace containing method being parsed.
    :return: List[Method]
    """
    # Match overall signature structure before handling individual parts.
    match = METHOD_SIGNATURE_PATTERN.search(text)
    if not match:
        raise InvalidMethodDeclaration(
            f'Signature does not match recognized pattern: {text}'
        )

    name = match['name']

    # Ensure method may be overridden.
    if match['ref'] == 'final':
        raise NonExtendableMethodError(
            f'{name} is declared final, however interface methods must '
            'be overridable.'
        )
    if not match['virtual'] and not match['ref'] == 'override':
        raise NonExtendableMethodError(
            f'Interface methods must be overridable, however {name} is not '
            'marked as a virtual method. Add "virtual" or "override" modifiers.'
        )

    # Determine return type.
    if match['return'] == 'auto':
        if not (return_type := match['tail_return']):
            raise InvalidMethodDeclaration(
                f'No return type declared in method signature: {text} '
                f'Inferred return types are not supported in interfaces.'
            )
    else:
        return_type = match['return']

    # Resolve return type if valid.
    try:
        return_type = resolve_type(return_type, profile, ns).name
    except InvalidTypeError as type_error:
        if return_type != 'void':
            raise InvalidReturnTypeError(str(type_error)) from type_error

    # Parse parameters
    params_text = match['params']
    for simplifying_pattern, replacement in COLLAPSED_PARAM_PATTERNS:
        params_text = simplifying_pattern.sub(params_text, replacement)

    parsed_params = [
        parse_param(param_text.strip(), profile, ns)
        for param_text in split_params(params_text)
    ]

    def create_signature_name(params: ty.List[Parameter]) -> str:
        signature_parameters = ','.join(str(param_.type) for param_ in params)
        cv = match['cv'] if match['cv'] else ''
        return f'{name}({signature_parameters}){cv}'

    signatures: ty.List[Method] = []
    used_params: ty.List[Parameter] = []
    for param in parsed_params:
        if param.optional:
            signatures.append(Method(
                create_signature_name(used_params),
                return_type=return_type,
                parameters=used_params.copy(),
            ))
        used_params.append(Parameter(param.name, param.type))
    signatures.append(Method(
        create_signature_name(used_params),
        return_type=return_type,
        parameters=used_params.copy(),
    ))
    return signatures


def split_params(text: str) -> ty.List[str]:
    """
    Splits passed parameter text into individual parameters.

    This acts similar to calling `.split(',')` on the parameter text,
    however it only splits on commas which are not embedded within a
    set of angle brackets (<>). Other bracket types are not handled as
    they are separable by a code observer taking advantage of the scopes
    denoted by code_walk().

    Additionally, unlike .split(), if an empty text is passed, the
    returned parameter list will be empty.

    :param text: Text containing all parameters to be split.
    :return: Split parameters.
    """
    params: ty.List[str] = []
    param = ''
    depth = 0
    for char in text:
        if char == ',' and depth == 0:
            params.append(param.strip())
            param = ''
        else:
            if char == '<':
                depth += 1
            elif char == '>':
                if depth <= 0:
                    raise InvalidMethodDeclaration(
                        f'Mismatched angle brackets in parameter list: {text}'
                    )
                depth -= 1
            param += char
    if depth > 0:
        raise InvalidMethodDeclaration(
            f'Mismatched angle brackets in parameter list: {text}'
        )
    if param:
        params.append(param.strip())
    return params


def parse_param(
        text: str, profile: Profile = Profile(), ns: str = ''
) -> ParsedParam:
    """
    Parses a single parameter's text.

    See parse_method().

    :param text: Parameter text (Ex: 'int* foo[]')
    :param profile: Profile containing types usable in parameters.
    :param ns: Namespace containing method being parsed.
    :return: Parsed parameter information.
    """
    match = PARAM_PATTERN.search(text)
    if not match:
        raise InvalidParamDeclaration(
            f'Unparseable method parameter: {repr(text)}.'
        )

    *refs, cv = parse_type_modifiers(match['cv'], match['type_suffix'])
    try:
        param_type = resolve_type(match['base_type'].strip(), profile, ns).name
        tparams = [
            parse_param(tparam.strip() + ' x', profile, ns).type
            for tparam in split_params(match['tparam'] or [])
        ]
    except InvalidTypeError as type_error:
        raise InvalidParamTypeError(str(type_error)) from type_error

    # Handle const-ref special case
    if cv.is_const and refs == [TypeRef('&')]:
        param_type += ' const&'
    elif cv.is_const or cv.is_volatile:
        raise ReferenceParamError(
            f'Unexpected cv qualification of method parameter: {text}'
        )
    elif refs or match['array']:
        raise ReferenceParamError(
            'Types which reference unowned data are unsupported in '
            'interface methods. This includes pointers (int*), C++ '
            'references (int&), and array parameters (int[]). '
            'Only const reference parameters are allowed as an exception, to '
            'allow unneeded copying to be avoided. '
            f'Got: {param_type}'
        )

    return ParsedParam(
        name=match['name'],
        type=param_type + ('<' + ','.join(tparams) + '>' if tparams else ''),
        optional=match['default'] is not None
    )


MODIFIER_PATTERN = re.compile(r'\*|&|const|volatile')


class TypeRef(ty.NamedTuple):
    type: str
    is_const: bool = False
    is_volatile: bool = False

    def __str__(self):
        const = ' const' if self.is_const else ''
        volatile = ' volatile' if self.is_volatile else ''
        return f'{self.type}{const}{volatile}'
    

def parse_type_modifiers(
        prefix: ty.Optional[str], suffix: ty.Optional[str] = ''
) -> ty.List[TypeRef]:
    prefix = prefix or ''
    suffix = suffix or ''
    raw_modifiers = prefix + suffix

    def tokenize(text: str) -> ty.List[str]:
        pos = 0
        tokens = []
        while True:
            match = MODIFIER_PATTERN.search(text, pos)
            if match is None:
                break
            pos = match.end()
            tokens.append(match.group())
        return tokens

    def parse_tokens(tokens: ty.List[str]) -> ty.List[TypeRef]:
        refs = []
        const = volatile = False
        for token in reversed(tokens):
            if token == 'const':
                const = True
            elif token == 'volatile':
                volatile = True
            else:
                assert token in '*&'
                refs.append(TypeRef(token, const, volatile))
                const = volatile = False
        refs.append(TypeRef('', const, volatile))
        return refs

    return parse_tokens(tokenize(raw_modifiers))


def resolve_type(
        name: str, profile: Profile, ns: str = ''
) -> ty.Union[Serializable, Interface, str]:
    """
    Resolves a name appearing in code to a serializable type
    or interface.

    :param name: Name appearing in code.
    :param profile: Profile containing known types.
    :param ns: Namespace containing name.
    :return: Resolved Serializable, Interface type
    :raises: InvalidTypeError if type cannot be resolved.
    """
    ns_parts = ns.split('::')
    if name.startswith('::'):
        ns_parts = []
        name = name[len('::'):]
    while True:
        checked_name = '::'.join(ns_parts + [name])
        for collection in (
                BUILTIN_TYPES, profile.serializable_types, profile.interfaces
        ):
            with contextlib.suppress(KeyError):
                return collection[checked_name]
        if not ns_parts:
            # Name has not been resolved.
            if name in UNSUPPORTED_INTS:
                raise InvalidTypeError(
                    f'{name!r} integer types are unsupported as their size may '
                    'vary across platforms. Use a fixed-width integer type '
                    'from <cstdint> instead.'
                )
            elif name in UNIMPLEMENTED_COLLECTIONS:
                raise InvalidTypeError(
                    f'Collection type: {name} is not currently supported.'
                )
            else:
                raise InvalidTypeError(
                    f'Name: {name!r} does not resolve to any type within '
                    f'namespace: {ns or "(root)"}'
                )
        ns_parts.pop()
    # TODO: Use with struct, method return type, and parse_param()


@functools.singledispatch
def remove_prefix(pattern: ty.Union[str, re.Pattern], text: str) -> str:
    """
    Removes prefix matching passed pattern from text.

    :param pattern: Regex pattern to match.
    :param text: Text to remove prefix from.
    :return: Text without prefix.
    """
    return remove_prefix(re.compile(pattern), text)


@remove_prefix.register
def _(pattern: re.Pattern, text: str) -> str:
    if match := pattern.match(text):
        text = text[match.end():]
    return text


BRACE_PAIRS = '{}', '[]', '()'
BRACE_START_CHARS = [brace_pair[0] for brace_pair in BRACE_PAIRS]
BRACE_END_CHARS = [brace_pair[1] for brace_pair in BRACE_PAIRS]


def _paired_brace(char: str) -> str:
    with contextlib.suppress(ValueError):
        index = BRACE_START_CHARS.index(char)
        return BRACE_END_CHARS[index]
    with contextlib.suppress(ValueError):
        index = BRACE_END_CHARS.index(char)
        return BRACE_START_CHARS[index]
    raise ValueError(f'Passed char {repr(char)} is not a brace.')
