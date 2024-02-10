from __future__ import annotations
from typing import TYPE_CHECKING

from alpaca.clr import AST, ASTToken
from alpaca.concepts import Type

from eisen.state.basestate import BaseState as State
from eisen.common.nodedata import NodeData
from eisen.validation.validate import Validate
import eisen.adapters as adapters

if TYPE_CHECKING:
    from eisen.typecheck.typechecker import TypeChecker

class CallUnwrapper():
    @staticmethod
    def process_and_restructure_ast(state: State, guessed_params_type: Type, fn: TypeChecker) -> Type:
        """decide whether or not the call needs to be unwrapped, and returns the
        true type of the parameters"""
        match CallUnwrapper._chains_to_correct_function(state, guessed_params_type):
            case None:
                return state.get_abort_signal()
            case True:
                return CallUnwrapper._promote_to_call(state, true_params_type=guessed_params_type)
            case False:
                return CallUnwrapper._restructure_extension_function(state, fn)

    @staticmethod
    def _promote_to_call(state: State, true_params_type: Type) -> Type:
        """
        As we know that the guessed_params_type are the [true_params_type], we have no work
        to do other than to promote the (raw_call ...) directly to a (call ...) AST.
        """
        state.get_ast().update(type="call")
        return true_params_type

    @staticmethod
    def _get_function_name_element(ast: AST) -> AST:
        """
        Given something like this:
            (raw_call (. (ref obj) attr) (params 1 2 3))
                                   ^^^^
        The function name is marked above.
        """
        return ast.first().second()

    @staticmethod
    def _get_first_parameter_element(ast: AST) -> AST:
        """
        Given something like this:
            (raw_call (. (ref obj) attr) (params 1 2 3))
                          ^^^^^^^
        The first parameter is marked above.
        """
        return ast.first().first()

    @staticmethod
    def _get_parameter_list(ast: AST) -> AST:
        """
        Given something like this:
            (raw_call (. (ref obj) attr) (params 1 2 3))
                                          ^^^^^^^^^^^^
        The parameter list is marked above. It is the last element
        """
        return ast[-1]

    @staticmethod
    def _create_fn_ast_element(state: State) -> AST:
        return AST(
            type="fn",
            lst=[CallUnwrapper._get_function_name_element(state.get_ast())],
            line_number=state.get_line_number(),
            data=NodeData())

    @staticmethod
    def _restructure_extension_function(state: State, fn: TypeChecker) -> Type:
        """
        Given something like this:
            (raw_call (. (ref obj) attr) (params 1 2 3))

        This method is called if we have identified that this is not a call of an attribute
        function, but rather an extension function. Therefore we must restructure the AST to this:
            (call (fn attr) (params (ref obj) 1 2 3))
        """

        parameter_list_element = CallUnwrapper._get_parameter_list(state.get_ast())
        first_param_element = CallUnwrapper._get_first_parameter_element(state.get_ast())

        # This will change the parameter list in place
        parameter_list_element[:] = [first_param_element, *parameter_list_element]
        fn_element = CallUnwrapper._create_fn_ast_element(state)

        # Update the (raw_call ...) to a (call ...) AST with the function element we just created
        # and the newly updated parameter list.
        state.get_ast().update(type="call", lst=[fn_element, parameter_list_element])

        # reapply the TypeChecker to get the correct type of the parameters
        true_type = fn.apply(state.but_with(ast=parameter_list_element))

        # attempt to lookup the function. If it does not exist, then report an exception.
        node = adapters.Fn(state.but_with_first_child())
        instance = node.resolve_function_instance(argument_type=true_type)
        if Validate.function_exists(state, node.get_name(), true_type, instance).failed():
            return state.get_abort_signal()
        return true_type

    @staticmethod
    def _chains_to_correct_function(state: State, guessed_params_type: Type) -> bool:
        match caller := state.get_ast().first():
            case AST(type="::"):
                return CallUnwrapper._follow_scope_to_resolution(state, scope_ast=caller)
            case AST(type="."):
                return CallUnwrapper._type_is_function(
                    type_=CallUnwrapper._follow_chain_to_get_type(state, ast=caller))
            case AST(type="ref"):
                node = adapters.Ref(state.but_with_first_child())
                if node.is_print(): return True
                return node.resolve_reference_type().is_function()
            case AST(type="fn"):
                node = adapters.Fn(state.but_with_first_child())
                instance = node.resolve_function_instance(argument_type=guessed_params_type)
                if Validate.function_exists(state, node.get_name(), guessed_params_type, instance).failed():
                    return None
                return instance.type.is_function()
        return False

    @staticmethod
    def _follow_scope_to_resolution(state: State, scope_ast: AST) -> bool:
        instance = adapters.ModuleScope(state.but_with(ast=scope_ast)).get_end_instance()
        return instance.type.is_function()

    @staticmethod
    def _type_is_function(type_: Type) -> bool:
        return type_ is not None and type_.is_function()

    @staticmethod
    def _follow_chain_to_get_type(state: State, ast: AST | ASTToken) -> Type | None:
        match ast:
            case AST(type="ref"): return adapters.Ref(state.but_with(ast=ast)).resolve_reference_type()
            case ASTToken(): return None
            case _:
                obj_type: Type = CallUnwrapper._follow_chain_to_get_type(state, ast.first())
                if obj_type is None: return None

                attr = ast.second().value
                if obj_type.has_member_attribute_with_name(attr):
                    return obj_type.get_member_attribute_by_name(attr)
                return None
