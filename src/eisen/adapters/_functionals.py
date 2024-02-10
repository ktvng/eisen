from __future__ import annotations

from alpaca.clr import AST, ASTToken
from alpaca.concepts import Type
from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.adapters.argsrets import ArgsRets
from eisen.common.eiseninstance import FunctionInstance
from eisen.adapters._decls import Colon

class CommonFunction(AbstractNodeInterface):
    ast_types = ["def", "create", ":="]
    examples = """
    (<ast_type> name
        (args ...)
        (rets ...)
        (seq ...))
    """
    get_name = AbstractNodeInterface.get_name_from_first_child

    def get_args_ast(self) -> AST:
        return self.second_child()

    def get_rets_ast(self) -> AST:
        return self.third_child()

    def get_seq_ast(self) -> AST:
        return self.state.get_ast()[-1]

    def enter_context_and_apply(self, fn) -> None:
        # must create fn_context here as it is shared by all children
        fn_context = self.state.create_block_context()
        for child in self.state.get_child_asts():
            fn.apply(self.state.but_with(
                ast=child,
                context=fn_context))


class Def(AbstractNodeInterface):
    ast_type = "def"
    examples = """
    (def name
        (args ...)
        (rets ...)
        (seq ...))
    """
    get_function_name = AbstractNodeInterface.get_name_from_first_child

    def get_args_ast(self) -> AST:
        return self.second_child()

    def get_rets_ast(self) -> AST:
        return self.third_child()

    def get_seq_ast(self) -> AST:
        return self.state.get_ast()[-1]

    def get_arg_names(self) -> list[str]:
        return self._unpack_to_get_names(self.get_args_ast())

    def get_ret_names(self) -> list[str]:
        return self._unpack_to_get_names(self.get_rets_ast())

    def has_return_value(self) -> list[str]:
        return not self.get_rets_ast().has_no_children()

    def get_function_instance(self) -> FunctionInstance:
        return self.state.get_instances()[0]

    def get_function_type(self) -> Type:
        return self.get_function_instance().type

    def has_function_as_argument(self) -> bool:
        return any(t.is_function() for t in self.get_function_instance()
                   .type
                   .get_argument_type()
                   .unpack_into_parts())

    def _unpack_to_get_names(self, args_or_rets: AST) -> list[str]:
        if args_or_rets.has_no_children():
            return []
        first_arg = args_or_rets.first()
        if first_arg.type == "prod_type":
            colonnodes = first_arg._list
        else:
            colonnodes = [first_arg]

        return [Colon(self.state.but_with(ast=node)).get_name() for node in colonnodes]


class Create(AbstractNodeInterface):
    ast_type = "create"
    examples = """
    1. wild
        (create
            (args ...)
            (rets ...)
            (seq ...))
    2. normalized
        (create struct_name
            (args ...)
            (rets ...)
            (seq ...))
    """

    def normalize(self, struct_name: str):
        """adds the struct name as the first parameter. this normalizes the structure
        of (def ...) and (create ...) asts so we can use the same code to process
        them"""
        self.state.get_ast()._list.insert(0, ASTToken(type_chain=["TAG"], value=struct_name))

    def get_args_ast(self) -> AST:
        return self.second_child()

    def get_rets_ast(self) -> AST:
        return self.third_child()

    def get_seq_ast(self) -> AST:
        return self.state.get_ast()[-1]

    def get_name(self) -> str:
        """the name of the constructor is the same as the struct it constructs. this
        must be passed into the State as a parameter"""
        return self.state.get_struct_name()

    def get_name_of_created_entity(self) -> str:
        return ArgsRets(self.state.but_with(ast=self.get_rets_ast())).get_names()[0]

    def get_type_of_created_entity(self) -> str:
        return ArgsRets(self.state.but_with(ast=self.get_rets_ast())).state.get_returned_type()
