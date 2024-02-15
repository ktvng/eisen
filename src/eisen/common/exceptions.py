from __future__ import annotations

from alpaca.concepts import AbstractException

class Exceptions():
    class UseBeforeInitialize(AbstractException):
        type = "UseBeforeInitialize"
        description = "variable cannot be used before it is initialized"

    class UndefinedVariable(AbstractException):
        type = "UndefinedVariable"
        description = "variable is not defined"

    class UndefinedFunction(AbstractException):
        type = "UndefinedFunction"
        description = "function is not defined"

    class UndefinedType(AbstractException):
        type = "UndefinedType"
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

    class NilUsage(AbstractException):
        type = "NilUsage"
        description = "cannot use a nilable type without first casting"

    class NilAssignment(AbstractException):
        type = "NilAssignment"
        description = "nil can only be assigned to a nilable type"

    class ObjectLifetime(AbstractException):
        type = "ObjectLifetime"
        description = "cannot assign an object to a reference when the object has a shorter lifetime than the reference"

    class NilableMismatch(AbstractException):
        type = "NilableMismatch"
        description = "a nilable type cannot be assigned to a non-nilable type"

    class NilCast(AbstractException):
        type = "NilCast"
        description = "cannot cast nilable into non-nilable if nilable value could be 'nil'"

    class IncompleteTraitDefinition(AbstractException):
        type = "IncompleteTraitDefinition"
        description = "a trait implementation is missing a required function"

    class MalformedTraitDeclaration(AbstractException):
        type = "DisallowedTraitDeclaration"
        description = "function declaration inside of a trait is malformed"

    class IncompleteInitialization(AbstractException):
        type = "IncompleteInitialization"
        description = "a member attribute of a struct is not initialized in the constructor"

    class Move(AbstractException):
        type = "Move"
        description = "can only move a let type"

    class ReferenceInvalidation(AbstractException):
        type = "ReferenceInvalidation"
        description = "reference is invalidated after memory unsafe operation"

    class CompilerAssertion(AbstractException):
        type = "CompilerAssertion"
        description = "failed compiler assertion annotation"

    class TooManyCurriedArguments(AbstractException):
        type = "TooManyCurriedArguments"
        description = "cannot curry more parameters than arguments to function"

    class IncompatibleBinding(AbstractException):
        type = "IncompatibleBinding"
        description = "declared binding is not compatible with provided binding"

    class PartialConditionalInitialization(AbstractException):
        type = "PartialConditionalInitialization"
        description = "all branches must initialize/not-initialize references"
