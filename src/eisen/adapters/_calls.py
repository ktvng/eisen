from __future__ import annotations

from alpaca.concepts import Type
from alpaca.clr import AST
from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.common.eiseninstance import EisenFunctionInstance
from eisen.common.restriction import GeneralRestriction

from eisen.adapters._refs import RefLike
from eisen.adapters._functionals import Def
from eisen.state.state_posttypecheck import State_PostTypeCheck

class _SharedMixins:
    def get_function_return_type(self) -> Type:
        return self.state.get_node_data().returned_type

    def get_function_argument_type(self) -> Type:
        return self.state.but_with_first_child().get_returned_type().get_argument_type()

class Call(AbstractNodeInterface, _SharedMixins):
    ast_type = "call"
    examples = """
    (call (fn ...) (params ... ))
    (call (:: mod (fn name)) (params ...)))))
    """
    def get_fn_instance(self) -> EisenFunctionInstance:
        return self.state.but_with_first_child().get_instances()[0]

    def get_fn_ast(self) -> AST:
        if self.state.but_with_first_child().get_ast().type != "::" and self.state.get_ast().type != "fn":
            raise Exception(f"unexpected ast type of {self.state.get_ast().type}")
        if self.stateast.type == "fn":
            return self.state.get_ast()
        return self._unravel_scoping(ast=self.state.get_ast().second())

    def get_function_name(self) -> str:
        return RefLike(self.state.but_with_first_child()).get_name()

    def get_function_return_restrictions(self) -> list[GeneralRestriction]:
        return self.get_function_return_type().get_restrictions()

    def is_print(self) -> bool:
        node = RefLike(self.state.but_with(ast=self.first_child()))
        return node.is_print()

    def is_append(self) -> bool:
        return RefLike(self.state.but_with(ast=self.first_child())).is_append()

    def get_params_ast(self) -> str:
        return self.state.get_ast()[-1]

    def get_param_names(self) -> list[str]:
        return Def(self.state.but_with(ast=self.get_ast_defining_the_function())).get_arg_names()

    def get_param_types(self) -> list[Type]:
        if not isinstance(self.state, State_PostTypeCheck):
            raise Exception("get_param_types can only be used after typechecker is run")
        return [self.state.but_with(ast=param).get_returned_type() for param in self.get_params()]

    def get_return_names(self) -> list[str]:
        return Def(self.state.but_with(ast=self.get_ast_defining_the_function())).get_ret_names()

    def get_ast_defining_the_function(self) -> AST:
        return self.state.but_with_first_child().get_instances()[0].ast

    def get_function_instance(self) -> EisenFunctionInstance:
        return self.state.but_with(ast=self.get_ast_defining_the_function()).get_instances()[0]

    def is_pure_function_call(self) -> bool:
        return self.first_child().type == "fn"

class RawCall(AbstractNodeInterface):
    ast_type = "raw_call"
    examples = """
    x.run() becomes:
        (raw_call (ref (. x run)) (params ))

    (raw_call (ref name) (params ...))
    """

    def get_ref_ast(self) -> AST:
        return self.first_child()

    def get_params_ast(self) -> AST:
        return self.third_child()

class CurriedCall(AbstractNodeInterface, _SharedMixins):
    ast_type = "curry_call"
    examples = """
        (curry_call (ref space) (curried 4)
    """

    def get_params_ast(self) -> AST:
        return self.second_child()
