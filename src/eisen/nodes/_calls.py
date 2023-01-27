from __future__ import annotations

from alpaca.concepts import Type
from alpaca.clr import CLRList
from eisen.nodes.nodeinterface import AbstractNodeInterface
from eisen.common.eiseninstance import EisenFunctionInstance
from eisen.common.restriction import GeneralRestriction

from eisen.nodes._refs import RefLike
from eisen.nodes._functionals import Def

class Call(AbstractNodeInterface):
    asl_type = "call"
    examples = """
    (call (fn ...) (params ... ))
    (call (:: mod (fn name)) (params ...)))))
    """
    def get_fn_instance(self) -> EisenFunctionInstance:
        return self.state.but_with_first_child().get_instances()[0]

    def get_fn_asl(self) -> CLRList:
        if self.state.but_with_first_child().get_asl().type != "::" and self.state.get_asl().type != "fn":
            raise Exception(f"unexpected asl type of {self.state.get_asl().type}")
        if self.stateasl.type == "fn":
            return self.state.get_asl()
        return self._unravel_scoping(asl=self.state.get_asl().second())

    def get_function_return_type(self) -> Type:
        return self.state.get_node_data().returned_type

    def get_function_argument_type(self) -> Type:
        return self.state.but_with_first_child().get_returned_type().get_argument_type()

    def get_function_name(self) -> str:
        return RefLike(self.state.but_with_first_child()).get_name()

    def get_function_return_restrictions(self) -> list[GeneralRestriction]:
        return self.get_function_return_type().get_restrictions()

    def is_print(self) -> str:
        node = RefLike(self.state.but_with(asl=self.first_child()))
        return node.is_print()

    def get_params_asl(self) -> str:
        return self.state.get_asl()[-1]

    def get_params(self) -> list[CLRList]:
        return self.get_params_asl()._list

    def get_param_names(self) -> list[str]:
        return Def(self.state.but_with(asl=self.get_asl_defining_the_function())).get_arg_names()

    def get_return_names(self) -> list[str]:
        return Def(self.state.but_with(asl=self.get_asl_defining_the_function())).get_ret_names()

    def get_asl_defining_the_function(self) -> CLRList:
        return self.state.but_with_first_child().get_instances()[0].asl

class RawCall(AbstractNodeInterface):
    asl_type = "raw_call"
    examples = """
    x.run() becomes:
        (raw_call (ref (. x run)) (params ))

    (raw_call (ref name) (params ...))
    """

    def get_ref_asl(self) -> CLRList:
        return self.first_child()

    def get_params_asl(self) -> CLRList:
        return self.third_child()

class CurriedCall(AbstractNodeInterface):
    asl_type = "curry_call"
    examples = """
        (curry_call (ref space) (curried 4)
    """
