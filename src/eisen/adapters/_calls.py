from __future__ import annotations

from alpaca.concepts import Type
from alpaca.clr import AST
from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.common.eiseninstance import FunctionInstance
from eisen.common.traits import TraitsLogic
from eisen.common.binding import Binding

from eisen.adapters._refs import RefLike
from eisen.adapters._functionals import Def

class _SharedMixins:
    def get_function_return_type(self) -> Type:
        return self.state.get_node_data().returned_type

    def get_function_argument_type(self) -> Type:
        return self.state.but_with_first_child().get_returned_type().get_argument_type()

    def get_function_definition_if_known(self) -> AST | None:
        """
        The function definition is the (def ...) or (create ...) AST which defines the function that
        is being called. It is trivially known if the call AST is of the form (call (fn func) ...)
        as the (fn ...) directly references the global function.

        There may be other cases where the function instance is known, but these would require more
        difficult logic and is not implemented
        """
        if self.state.but_with_first_child().get_instances() is None: return None
        maybe_defining_ast = self.state.but_with_first_child().get_instances()[0].ast
        match maybe_defining_ast.type:
            case "def": return maybe_defining_ast
            case "create": return maybe_defining_ast
            case _: return None

    def get_param_names(self) -> list[str]:
        """
        Return the names of the called function's parameters if known. If a function is invoked
        directly (call (fn someFunction) ...), this will be known, but if a function is called
        with any indirection as through a variable or a curried object
        (call (ref someFunctionVariable) ...) this will not be known. In the case that the names of
        the function parameters are not known, a parameter name is made up.
        """

        # parameter names are known if we know the actual AST defining the function
        defining_ast = self.get_function_definition_if_known()
        if defining_ast:
            return Def(self.state.but_with(ast=defining_ast)).get_arg_names()

        # make up parameter names
        return [f"param #{i+1}" for i in range(len(self.second_child()))]

    def get_params_ast(self) -> str:
        return self.state.get_ast()[-1]

class Call(AbstractNodeInterface, _SharedMixins):
    ast_type = "call"
    examples = """
    (call (fn ...) (params ... ))
    (call (:: mod (fn name)) (params ...)))))
    """

    def get_return_value_bindings(self) -> list[Binding]:
        return [t.modifier for t in self.get_function_return_type().unpack_into_parts()]

    def get_argument_bindings(self) -> list[Binding]:
        return [t.modifier for t in self.get_function_argument_type().unpack_into_parts()]

    def get_function_name(self) -> str:
        return RefLike(self.state.but_with_first_child()).get_name()

    def is_print(self) -> bool:
        node = RefLike(self.state.but_with(ast=self.first_child()))
        return node.is_print()

    def is_append(self) -> bool:
        return RefLike(self.state.but_with(ast=self.first_child())).is_append()

    def get_function_instance(self) -> FunctionInstance:
        return self.state.but_with(ast=self.get_function_definition_if_known()).get_instances()[0]

    def is_pure_function_call(self) -> bool:
        return self.first_child().type == "fn" or self.first_child().type == "::"

    def is_trait_function_call(self) -> bool:
        return TraitsLogic.are_trait_arguments(self.state, self.get_function_argument_type())

    def get_caller_type(self) -> Type:
        """
        For cases with (call (. (ref caller) attr_func) ...), return the type of the caller
        """
        return self.state.but_with(ast=self.state.get_ast().first().first()).get_returned_type()

class RawCall(AbstractNodeInterface):
    ast_type = "raw_call"
    examples = """
    x.run() becomes:
        (raw_call (ref (. x run)) (params ))

    (raw_call (ref name) (params ...))
    """

class CurriedCall(AbstractNodeInterface, _SharedMixins):
    ast_type = "curry_call"
    examples = """
        (curry_call (ref space) (curried 4)
    """
