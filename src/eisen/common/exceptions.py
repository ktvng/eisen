from __future__ import annotations

from alpaca.concepts import AbstractException

class Exceptions():
    class MemoryTypeMismatch(AbstractException):
        type = "MemoryTypeMismatch"
        description = "cannot assign due to let/var/val differences"

    class UseBeforeInitialize(AbstractException):
        type = "UseBeforeInitialize"
        description = "variable cannot be used before it is initialized"

    class UndefinedVariable(AbstractException):
        type = "UndefinedVariable"
        description = "variable is not defined"

    class UndefinedFunction(AbstractException):
        type = "UndefinedFunction"
        description = "function is not defined"

    class UnderfinedType(AbstractException):
        type = "UndefiedType"
        description = "type is not defined"

    class RedefinedIdentifier(AbstractException):
        type = "RedefinedIdentifier"
        description = "identifier is already in use"

    class TypeMismatch(AbstractException):
        type = "TypeMismatch"
        description = "type different from expected"

    class TupleSizeMismatch(AbstractException):
        type = "TupleSizeMismatch"
        description = "tuple unpack requires equal sizes"

    class CastIncompatibleTypes(AbstractException):
        type = "CastIncompatibleTypes"
        description = "casting a type into an un-inherited type"

    class MissingAttribute(AbstractException):
        type = "MissingAttribute"
        description = "missing a required attribute"

    class AttributeMismatch(AbstractException):
        type = "AttributeMismatch"
        description = "attribute exists but is the wrong type"

    class EmbeddedStructCollision(AbstractException):
        type = "EmbeddedStructCollision"
        description = "embedded structs cannot have an attribute with the same name and type as another"

    class LiteralAssignment(AbstractException):
        type = "LiteralAssignment"
        description = "an entity declared with the 'var' keyword may not be assigned to a literal"

    class NilUsage(AbstractException):
        type = "NilUsage"
        description = "cannot use a nilable type without first casting"

    class NilAssignment(AbstractException):
        type = "NilAssignment"
        description = "nil can only be assigned to a nilable type"

    class ObjectLifetime(AbstractException):
        type = "ObjectLifetime"
        description = "cannot assign an object to a reference when the object has a shorter lifetime than the reference"

    class MemoryAssignment(AbstractException):
        type = "MemoryAssignment"
        description = "incompatible assignment of let/var/val declared types"

    class LetReassignment(AbstractException):
        type = "LetReassignment"
        description = "memory is allocated with the the 'let' keyword and already initialized cannot be overriden with the '=' operation"

    class LetInitializationMismatch(AbstractException):
        type = "LetInitializationMismatch"
        description = "the 'let' keyword allocates a block of memory which must be initialized by a function returning a 'let' designation"

    class VarImproperAssignment(AbstractException):
        type = "VarImproperAssignment"
        description = "the 'var' keyword defines a pointer to an existing memory allocation and cannot be set to point to a literal"

    class NilableMismatch(AbstractException):
        type = "NilableMismatch"
        description = "a nilable type cannot be assigned to a non-nilable type"

    class NilCast(AbstractException):
        type = "NilCast"
        description = "cannot cast nilable into non-nilable if nilable value could be 'nil'"

    class PrimitiveAssignmentMismatch(AbstractException):
        type = "PrimitiveAssignmentMismatch"
        description = "a primitive type may only be assigned to other primitives or literals"

    class IncompleteInitialization(AbstractException):
        type = "IncompleteInitialization"
        description = "a member attribute of a struct is not initialized in the constructor"

    class ImmutableVal(AbstractException):
        type = "ImmutableVal"
        description = "cannot modify a value or any of its state"

    class Move(AbstractException):
        type = "Move"
        description = "can only move a let type"

    class ReferenceInvalidation(AbstractException):
        type = "ReferenceInvalidation"
        description = "referece is invalidated after memory unsafe operation"
