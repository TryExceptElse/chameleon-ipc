# Chameleon IPC (cipc)

Chameleon IPC is an IPC/RPC system which blends into the surrounding
code, using annotated C++ interface headers as its IDL.

## WIP notice

_This project is currently a work-in-progress. It is not yet usable._

## Purpose

Chameleon IPC (or _cipc_) was created to allow seamless IPC communication
between processes using existing C++ types.

This has several advantages over other RPC approaches:

* Developers can avoid creating separate types
* _cipc_ removes the need for developers to produce duplicate IDL and
  C++ object definitions.
* _cipc_ allows additional non-virtual methods to be added to interfaces
  as needed, allowing more convenient interfaces to be exposed than is
  generally possible using generated interface code.
* C++ methods are immediately visible to developers in a form they are
  already familiar with. C++ method signatures are not hidden in
  generated files located somewhere in build output directories.
* C++ methods and types can be documented as normal, without needing to
  locate generated sources or documentation files.

## Features

* ABI abstraction: As with other IPC mechanisms, _cipc_ allows apps
  compiled with different compiler or standard library versions to
  communicate with each other.
* API flexibility: _cipc_ allows structs and interfaces to introduce
  new fields or methods, or rearrange existing fields and methods
  without breaking backwards compatibility.

## Interface declaration

### IPC decorators

* @IPC(Serializable)
* @IPC(Interface)
* @IPC(Method)
* @IPC(Callback)
* @IPC(CallbackRegister)
* @IPC(CallbackRemove)

### Builtin types

#### Number types

* __std::uint8_t__
* __std::uint16_t__
* __std::uint32_t__
* __std::uint64_t__
* __std::int8_t__
* __std::int16_t__
* __std::int32_t__
* __std::int64_t__
* __std::size_t__
* __int__
* __float__
* __double__
* __bool__

_Note: `char` is not supported as a builtin to avoid ambiguity
between signed and unsigned versions.
Depending on need, use `std::uint8_t` or `std::int8_t`_.

#### Complex types

* __std::deque__
* __std::list__
* __std::map__
* __std::multimap__
* __std::multiset__
* __std::optional__
* __std::set__
* __std::string__
* __std::unordered_map__
* __std::unordered_set__
* __std::vector__

## Internal object representation

### Serializable types

A Serializable object is one which has specializations of the
`cipc::serialize()` and `cipc::deserialize()` methods. Serializable
types are the only types which may be passed back and forth across
the IPC channel.

For the vast majority of use cases, objects may be made serializable
through the following steps:

* Ensure the type does not store any pointers or references.
* Ensure the type's members are themselves all Serializable.
* Ensure the type's members are all directly assignable by
  `cipc::serialize` and `cipc::deserialize`.
* Ensure the type is default constructable.
* Add an `// @IPC(Serializable)` annotation before the `struct`
  or `class`

Alternatively, custom `cipc::serialize()` and `cipc::deserialize()`
implementations may be provided, accepting the type to be serialized
as an argument.

_Note: `cipc::serialize()` and `cipc::deserialize()`
implementations must retain consistent output in order to avoid
breaking compatibility between versions._

#### Serializable field annotation

Serializable structs may be declared with `auto=True` as an annotation
parameter, indicating that the type may be auto-serialized, with all
fields being serialized and deserialized, or with `auto=False`, with
fields to be serialized marked with a `// @IPC(Field)` annotation.

__Auto-serialization example:__

```cpp
// @IPC(Serializable)
struct Foo {
  std::size_t id;
  std::string name;
};
```

__Explicit-fields example:__

```cpp
// @IPC(Serializable, auto=False)
class Foo {
 public:
  Foo() : id(1), name("foo") {}

  Foo(const Foo& other) = default;
  Foo(Foo&& other) = default;

  Foo& operator=(const Foo& other) = default;
  Foo& operator=(Foo&& other) = default;

  auto full_name() const -> std::string {
    return name + std::to_string(id);
  }

  // @IPC(Field)
  std::size_t id;
  // @IPC(Field)
  std::string name;
  std::size_t cached_hash;  // Not serialized.
};
```

#### Struct serialization format

Types annotated with `// @IPC(Serializable)` are serialized with the
following layout:

FIELD_HEADER : METADATA : PADDING? : SERIALIZED_VALUE : PADDING?

* FIELD_HEADER : 4B field summary. Contains the following bits:
  * Extended field ID length: 2b: Indicates whether 0-3 extra 4B field
    ID words (4B) are present.
  * Field size bit: 3b: Indicates size of value, or 0 if extra value
    size word will follow field ID.
  * Padding count: 3b: Indicates number of padding bytes between
    metadata and serialized value.
  * Field ID: 24b (3B): First 3 bytes of field ID.
* METADATA: Contains extended field ID and field size words.
* PADDING: Contains padding required to position serialized value at
  an ideal alignment for access. Length in bytes is indicated by header.
  Padding will not exceed 7B.
* SERIALIZED_VALUE: Value as serialized by `cipc::serialize()`.
* PADDING: Contains padding required to word-align any field
  which follows.

### Interface types

Interface types are types which are exposed for use by other processes.

Interface types must follow several rules:

* Interface types may not have any member fields
  * Interface implementations may of course implement as many fields as
    needed, but the Interface definition may not.
* Interface types shall be annotated with `// @IPC(Interface)`

### Publisher

A Publisher wraps an interface implementation and makes calls to its
methods on behalf of a client-side Proxy.

A Publisher type is generated for each annotated Interface type, and
is easily instantiated by the user on the IPC server-side.

```c++
#include "cipc/ipc.h"

#include "project/retro_encabulator.h"

#include "encabulator.cipc.h"  // Generated header.

int main() {
    cipc::Service ipc_service("file:///var/encabulator");  // Set up Unix pipe.
    RetroEncabulator impl;  // Implementation of the Encabulator interface.
    EncabulatorPublisher(impl, &ipc_service);
    ipc_service.Run();
}
```

### Proxy

A Proxy implements an Interface type, and relays calls to a remote
Publisher. Proxy types are Serializable, and are passed over IPC channels
in place of interface implementation objects.

```c++
#include "cipc/ipc.h"

#include "project/interfaces/encabulator.h"  // Interface definition.

int main() {
    cipc::Client ipc_client("file:///var/encabulator");
    auto* encabulator = ipc_client.get<Encabulator>();
    encabulator->AvertSideFumbling();
}
```

_Note that the client side does not need to include any
generated headers._

### Calling convention

Messages calling a method (whether regular RPC calls or callbacks) are
formatted as follows:

HEADER : METHOD_ID : OBJECT_ID : ARGUMENTS

* HEADER: 32b (4B): Contains the following bitfields:
  * Preamble: 8b : 0xC: Helps detect malformed messages, in combination
    with the following 'Message type' field.
  * Message type: 8b. Should be checked before any following fields.
    * 1 for 'call' messages.
  * Call ID: 16b (2B): Identifier for this method call. Allows return
    value to be paired with original method call.
* METHOD_ID: 32b (4B): Method ID
* OBJECT_ID: 64b (8B) Identifier of object being called.
  * 0 (null) Indicates that the service object is being called.
* Args: Size and types determined from method ID.

Return values are formatted more simply:

HEADER : VALUE

* HEADER: 32b (4B): Modified form of the call header.
  Contains the following bitfields:
  * Preamble: 8b : 0xC: Helps detect malformed messages, in combination
    with the following 'Message type' field.
  * Message type: 8b. Should be checked before any following fields.
    * 2 for 'response' messages.
  * Call ID: 16b (2B): Identifier for call being responded to.
* VALUE: Return value. Size and type determined from method ID.

## Project organization

### cipcc

* parser.py : Parses interface headers into 
  intermediate representation.
* codegen.py : Produces C++ Endpoint and Proxy objects which
  implement defined interfaces.

### libcipc

* serialize.h/.cc : Serialization utilities.
* channel : Bidirectional IPC implementation.
  May wrap Unix sockets or other mechanisms.

### cmake

* cipc.cmake : Provides convenience function for generating IPC
  implementations for all annotated interfaces within a target.
