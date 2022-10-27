from __future__ import annotations

from alpaca.validator import AbstractException

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
        description = "embedded structs cannot have an attribute with the same name and typeclass as another"

    class MemoryAssignment(AbstractException):
        type = "MemoryAssignment"
        description = "incompatible assignment of let/var/val declared types"

    class LiteralAssignment(AbstractException):
        type = "LiteralAssignment"
        description = "an entity declared with the 'var' keyword may not be assigned to a literal"