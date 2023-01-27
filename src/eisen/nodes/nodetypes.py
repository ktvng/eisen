from __future__ import annotations
from typing import TYPE_CHECKING

from alpaca.clr import CLRToken, CLRList
from alpaca.concepts._type import Type
from alpaca.concepts._module import Module
from alpaca.concepts._typefactory import TypeFactory

from eisen.common import implemented_primitive_types
from eisen.common.eiseninstance import EisenInstance, EisenFunctionInstance
from eisen.common.state import State
from eisen.common.restriction import (GeneralRestriction, LetRestriction, VarRestriction,
    PrimitiveRestriction, NullableVarRestriction)

from eisen.validation.lookupmanager import LookupManager

if TYPE_CHECKING:
    from eisen.validation.typechecker import TypeChecker

def get_name_from_first_child(self) -> str:
    """assumes the first child is a token containing the name"""
    return self.state.first_child().value

def first_child_is_token(self) -> bool:
    """true if the first child is a CLRToken"""
    return isinstance(self.first_child(), CLRToken)

def get_type_for_node_that_defines_a_type(self) ->Type:
    """returns the type for either a struct/interface node which defines a type."""
    return self.state.get_enclosing_module().get_defined_type(self._get_name())
