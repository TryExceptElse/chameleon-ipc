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
Module containing interface Profile.
"""
import enum
import dataclasses
from dataclasses import dataclass
import typing as ty


class Profile:
    """
    Class storing a collection of parsed interfaces and
    associated information.
    """
    serializable_types: ty.Dict[str, 'Serializable']
    interfaces: ty.Dict[str, 'Interface']

    def __init__(self) -> None:
        self.serializable_types = {}
        self.interfaces = {}


@dataclass
class Serializable:
    """
    Stores information about a serializable type.
    """
    class Type(enum.Enum):
        ENUM = 'enum'
        STRUCT = 'struct'

    name: str  # Type name, as it appears in C++.
    type: Type


@dataclass
class SerializableStruct(Serializable):
    fields: ty.Dict[str, 'Field'] = dataclasses.field(default_factory=dict)


class Field(ty.NamedTuple):
    """
    Named tuple storing information about a serializable field.
    """
    name: str
    type_name: str


@dataclass
class Interface:
    """
    Stores information about an addressable CIPC interface type.

    Interface types are exposed to connections from other applications,
    and have fixed addresses, by which they are identified to
    other processes.

    Overloads are considered separate methods for CIPC's purposes.
    """
    name: str  # Type name, as it appears in C++.
    methods: ty.Dict[str, 'Method']
    callbacks: ty.Dict[str, 'Callback']


@dataclass
class Method:
    """
    Stores information about a specific interface method.
    """
    name: str  # method name, as it appears in C++.


@dataclass
class Callback:
    """
    Stores information about a specific interface callback.
    """
    name: str
    register_method: str
    remove_method: str
