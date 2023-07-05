from __future__ import annotations
from typing import TYPE_CHECKING

from alpaca.clr import AST
from alpaca.concepts import Type, TypeFactory

from eisen.state.basestate import BaseState as State
from eisen.validation.builtin_print import Builtins
from eisen.common.nodedata import NodeData
from eisen.validation.validate import Validate
import eisen.adapters as adapters

if TYPE_CHECKING:
    from eisen.validation.typechecker import TypeChecker

class CallUnwrapper():
    @classmethod
    def process(cls, state: State, guessed_params_type: Type, fn: TypeChecker) -> Type:
        """decide whether or not the call needs to be unwrapped, and returns the
        true type of the parameters"""
        if cls._chains_to_correct_function(state, guessed_params_type):
            state.get_ast().update(type="call")
            return guessed_params_type
        else:
            # TODO: update type of params ast
            params_ast = state.get_ast()[-1]
            first_param_ast = state.get_ast().first().first()
            params_ast[:] = [first_param_ast, *params_ast]
            fn_ast = AST(
                type="fn",
                lst=[state.get_ast().first().second()],
                line_number=state.get_line_number(),
                data=NodeData())

            state.get_ast().update(type="call", lst=[fn_ast, params_ast])

            # Need to get the type of the first parameter
            first_param_type = fn.apply(state.but_with(ast=first_param_ast))
            if len(params_ast) == 1:
                true_type = first_param_type
            else:
                if guessed_params_type.is_tuple():
                    true_type = TypeFactory.produce_tuple_type(
                        components=[first_param_type, *guessed_params_type.components])
                else:
                    true_type = TypeFactory.produce_tuple_type(
                        components=[first_param_type, guessed_params_type])

            state.but_with_second_child().get_node_data().returned_type = true_type
            return true_type

    @classmethod
    def _chains_to_correct_function(cls, state: State, guessed_params_type: Type) -> bool:
        if state.get_ast().first().type == "ref":
            node = adapters.Ref(state.but_with_first_child())
            if node.is_print():
                return Builtins.get_type_of_print(state)
            return node.resolve_reference_type().is_function()
        if state.get_ast().first().type == "fn":
            node = adapters.Fn(state.but_with_first_child())
            instance = node.resolve_function_instance(argument_type=guessed_params_type)
            return instance.type.is_function()
        type = cls._follow_chain(state, state.get_ast().first())

        if type is None:
            return False
        if type.is_function():
            return True
        return False

    @classmethod
    def _follow_chain(cls, state: State, scope_ast: AST) -> Type:
        if scope_ast.type == "::":
            instance = adapters.ModuleScope(state.but_with(ast=scope_ast)).get_end_instance()
            return instance.type

        if scope_ast.type == ".":
            obj_type: Type = cls._follow_chain(state, scope_ast.first())
            if obj_type is None:
                return None
            attr = scope_ast.second().value
            if obj_type.has_member_attribute_with_name(attr):
                return obj_type.get_member_attribute_by_name(attr)
            else:
                return None
