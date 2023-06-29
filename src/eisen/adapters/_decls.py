from __future__ import annotations

from alpaca.clr import CLRList
from alpaca.concepts import Type
from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.common.restriction import GeneralRestriction, LetRestriction, VarRestriction, NullableVarRestriction, ValRestriction, FunctionalRestriction

class IletIvar(AbstractNodeInterface):
    asl_types = ["ilet", "ivar"]
    examples = """
    1. (ilet name (call ...))
    2. (ilet name 4)
    3. (ilet name (<expression>))
    4. (ilet (tags ...) (tuple ...))
    5. (ilet (tags ...) (call ...))
    """

    def get_names(self) -> list[str]:
        if isinstance(self.first_child(), CLRList):
            return [token.value for token in self.first_child()]
        return [self.first_child().value]

    def get_assigned_types(self) -> list[Type]:
        return self.state.but_with(asl=self.second_child()).get_returned_type().unpack_into_parts()

    def assigns_a_tuple(self) -> bool:
        return isinstance(self.first_child(), CLRList)

    def get_restriction(self) -> GeneralRestriction:
        if self.state.asl.type == "ilet":
            return LetRestriction()
        if self.state.asl.type == "ivar?":
            return NullableVarRestriction()
        else:
            return VarRestriction()


class Decl(AbstractNodeInterface):
    asl_types = ["let", "var", "val", "var?", ":"]
    examples = """
    1. multiple assignment
        (ASL_TYPE (tags ...) (type ...))
    2. single_assignment
        (ASL_TYPE name (type ...))
    """
    is_single_assignment = AbstractNodeInterface.first_child_is_token

    def get_restriction(self) -> GeneralRestriction:
        if self.get_node_type() == "let":
            return LetRestriction()
        if self.get_node_type() == "var":
            return VarRestriction()
        if self.get_node_type() == "val":
            return ValRestriction()
        if self.get_node_type() == "var?":
            return NullableVarRestriction()
        if self.get_node_type() == ":":
            if self.second_child().type == "var_type":
                return VarRestriction()
            elif self.second_child().type == "var_type?":
                return NullableVarRestriction()
            elif self.second_child().type == "type":
                return LetRestriction()
            elif self.second_child().type == "fn_type":
                return FunctionalRestriction()

        raise Exception(f"not implemented for {self.get_node_type()} {self.state.asl}")

    def get_is_nullable(self) -> bool:
        return self.get_node_type() == "var?"

    def get_is_nilable(self) -> bool:
        node_type = self.get_node_type()
        return (node_type == "var"
             or node_type == ":" and self.get_type_asl().type == node_type == "var_type?")

    def get_is_var(self) -> bool:
        node_type = self.get_node_type()
        return (node_type == "var"
            or node_type == "var?"
            or node_type == ":" and self.get_type_asl().type == "var_type?")

    def get_names(self) -> list[str]:
        if self.is_single_assignment():
            return [self.first_child().value]
        else:
            return [child.value for child in self.first_child()]

    def get_type_asl(self) -> CLRList:
        return self.second_child()
