from __future__ import annotations

from alpaca.clr import CLRList, CLRToken
from eisen.nodes.nodeinterface import AbstractNodeInterface
from eisen.common.eiseninstance import EisenFunctionInstance

class CommonFunction(AbstractNodeInterface):
    asl_types = ["def", "create", ":="]
    examples = """
    (<asl_type> name
        (args ...)
        (rets ...)
        (seq ...))
    """
    get_name = AbstractNodeInterface.get_name_from_first_child

    def get_args_asl(self) -> CLRList:
        return self.second_child()

    def get_rets_asl(self) -> CLRList:
        return self.third_child()

    def get_seq_asl(self) -> CLRList:
        return self.state.get_asl()[-1]

    def enter_context_and_apply(self, fn) -> None:
        # must create fn_context here as it is shared by all children
        fn_context = self.state.create_block_context()
        will_enter_constructor = self.state.asl.type == "create"
        for child in self.state.get_child_asls():
            fn.apply(self.state.but_with(
                asl=child,
                context=fn_context,
                inside_constructor=will_enter_constructor))


class Def(AbstractNodeInterface):
    asl_type = "def"
    examples = """
    (def name
        (args ...)
        (rets ...)
        (seq ...))
    """
    get_function_name = AbstractNodeInterface.get_name_from_first_child
    def get_args_asl(self) -> CLRList:
        return self.second_child()

    def get_rets_asl(self) -> CLRList:
        return self.third_child()

    def get_seq_asl(self) -> CLRList:
        return self.state.asl[-1]

    def get_arg_names(self) -> list[str]:
        return Def._unpack_to_get_names(self.get_args_asl())

    def get_ret_names(self) -> list[str]:
        return Def._unpack_to_get_names(self.get_rets_asl())

    def has_return_value(self) -> list[str]:
        return not self.get_rets_asl().has_no_children()

    def get_function_instance(self) -> EisenFunctionInstance:
        return self.state.get_instances()[0]

    @classmethod
    def _unpack_to_get_names(self, args_or_rets: CLRList) -> list[str]:
        if args_or_rets.has_no_children():
            return []
        first_arg = args_or_rets.first()
        if first_arg.type == "prod_type":
            colonnodes = first_arg._list
        else:
            colonnodes = [first_arg]

        return [node.first().value for node in colonnodes]


class Create(AbstractNodeInterface):
    asl_type = "create"
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
        of (def ...) and (create ...) asls so we can use the same code to process
        them"""
        self.state.get_asl()._list.insert(0, CLRToken(type_chain=["TAG"], value=struct_name))

    def get_args_asl(self) -> CLRList:
        return self.second_child()

    def get_rets_asl(self) -> CLRList:
        return self.third_child()

    def get_name(self) -> str:
        """the name of the constructor is the same as the struct it constructs. this
        must be passed into the State as a parameter"""
        return self.state.get_struct_name()

class IsFn(AbstractNodeInterface):
    asl_type = "is_fn"
    examples = """
    1. wild
        (is
            (args ...)
            (rets ...)
            (seq ...))
    """

    def normalize(self, variant_name: str):
        self.state.get_asl()._list.insert(0, CLRToken(type_chain=["TAG"], value="is_" + variant_name))

    def get_name(self) -> str:
        return "is_" + self.state.get_variant_name()
