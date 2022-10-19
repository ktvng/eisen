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
    