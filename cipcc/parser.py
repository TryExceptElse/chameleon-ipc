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
import functools
import re
from dataclasses import dataclass
import enum
from pathlib import Path
import typing as ty

from .interface import (
    Profile,
    Serializable,
    SerializableStruct,
    Field,
    Interface,
    Method,
    Callback
)


class ParsingError(RuntimeError):
    """Exception raised when invalid input code is received."""

    def __init__(self, state: 'CodeState', msg: str) -> None:
        super().__init__(f'On line {state.line_no}, col: {state.col_no}: {msg}')


class InvalidFieldDeclaration(ValueError):
    """
    Exception produced when _parse_fields() is given an
    invalid declaration.
    """


class InvalidAnnotation(ValueError):
    """
    Exception raised when an annotation with invalid format
    is encountered.
    """


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
        if char in '/*' and state.commented_line.endswith('/'):  # Comment start
            state.comment_start = '/' + char
            state.line = state.line[:-1]
            state.scope_text[state.scope_index] = \
                state.scope_text[state.scope_index][:-1]
        elif all((
            state.comment_start == '/*',
            char == '/',
            state.commented_line.endswith('*')
        )):
            state.comment_start = ''

        # Handle code constructs.
        if char == '\n':
            state.notify(CodeEvent.LINE_END)
            state.line = ''
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
        else:
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


class Parser:
    """
    Class handling parsing of interface descriptions from
    annotated headers.
    """

    def __init__(self):
        pass

    def parse(self, headers: ty.Iterable[Path]) -> Profile:
        """
        Parses set of interface files, and produces an
        interface Profile.

        :param headers: Interface headers to parse.
        :return: Profile containing parsed interfaces.
        """
        profile = Profile()

        def watch_for_root_annotations(_, state: 'CodeState') -> None:
            annotation = parse_annotations(state.line)
            if not annotation:
                return
            kwargs = annotation.kwargs
            if annotation.key == 'Serializable':
                state.add_observer(SerializableCodeObserver(profile, **kwargs))
            elif annotation.key == 'Interface':
                state.add_observer(InterfaceCodeObserver(profile))

        for header in headers:
            if header.is_dir():
                raise ValueError(
                    f'Passed path: {header} is a directory, not a header.'
                )
            text = header.read_text()
            root_observer = CodeObserver(
                watch_for_root_annotations, events=CodeEvent.LINE_END
            )
            code_walk(text, header.name, [root_observer])

        return profile


class SerializableCodeObserver(CodeObserver):
    """Handles serializable type declarations."""

    DECLARATION_PATTERN = re.compile(
        r'(?P<type>struct|class|enum) +(?:\S+ +)*(?P<name>\w+) *{'
    )

    def __init__(self, profile: Profile, auto: bool = True) -> None:
        """
        Initializes SerializableCodeObserver.

        :param profile: Profile to add parsed Serializable to.
        """
        super().__init__(self.__call__, CodeEvent.BRACKET_START)
        self.auto = auto
        self.name = None
        self.scope_brace_stack = []
        self.profile = profile
        self.serializable = None
        self.field_observer = None

    def __call__(self, event: 'CodeEvent', state: 'CodeState') -> None:
        if event == CodeEvent.BRACKET_START:
            match = self.DECLARATION_PATTERN.match(state.line)
            if not match:
                raise ParsingError(
                    state,
                    'Serializable type had unrecognized declaration: '
                    f'{repr(state.line)}.'
                )
            self.name = match['name']
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

        try:
            for field in parse_fields(state.statement):
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
            try:
                for field in parse_fields(statement):
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

    def __init__(self, profile: Profile) -> None:
        handled_events = CodeEvent.LINE_END | CodeEvent.BRACKET_END
        super().__init__(self.__call__, handled_events)
        self.name = None
        self.profile = profile

    def __call__(self, event: 'CodeEvent', state: 'CodeState') -> None:
        if not self.name:
            pass  # TODO


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


def parse_fields(text: str) -> ty.List['Field']:
    """
    Parse fields from field declaration statement.

    :param text: Declaration text (Ex: 'int foo = 1, baz = 2')
    :return: List of fields parsed from declaration.
    """
    # Split preceding label (Ex: 'public:')
    match = LABEL_REGEX.match(text)
    if match:
        text = text[len(match.group()):]

    # Parse type_name.
    parts = text.split(',')
    match = FIELD_TYPE_NAME_PATTERN.match(parts[0])
    if not match:
        raise InvalidFieldDeclaration(
            f'Invalid or unrecognized field declaration: {repr(text.strip())}. '
            'Ensure a cipc-supported type is being used. '
            'See the Serializable types docs.'
        )
    type_name = match['type_name']

    # Parse fields.
    parts[0] = parts[0][len(match.group()):]
    fields = []
    for part in parts:
        match = FIELD_NAME_PATTERN.match(part)
        if not match:
            raise InvalidFieldDeclaration(
                f'Unrecognized field declaration: {repr(text.strip())}.'
            )
        name = match['name']
        fields.append(Field(name, type_name))
    return fields


LABEL_REGEX = re.compile(r'^\s+(?P<label>\w+):\s')
FIELD_TYPE_NAME_PATTERN = re.compile(r'^\s*(?P<type_name>[\w:<>]+)\s+')
FIELD_NAME_PATTERN = re.compile(r'^\s*(?P<name>\w+)')


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
