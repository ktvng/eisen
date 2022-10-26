from __future__ import annotations

from alpaca.clr import CLRToken, CLRList
from alpaca.concepts._typeclass import TypeClass

from seer._params import Params

def get_name_from_first_child(self) -> str:
    return self.state.first_child().value

def first_child_is_token(self) -> bool:
    return isinstance(self.first_child(), CLRToken)

def get_typeclass_for_node_that_defines_a_typeclass(self) ->TypeClass:
    return self.state.get_module().get_typeclass_by_name(self._get_name())


class Nodes():
    class AbstractNodeInterface():
        def __init__(self, state: Params):
            self.state = state

        def first_child(self):
            return self.state.first_child()

        def second_child(self):
            return self.state.asl.second()

        def third_child(self):
            return self.state.asl.third()

    class Struct(AbstractNodeInterface):
        asl_type = "struct"
        examples = """
        (struct name 
            (impls ...) 
            (: ...) 
            (: ...) 
            (create ...))
        """
        _get_name = get_name_from_first_child
        get_struct_name = _get_name
        get_this_typeclass = get_typeclass_for_node_that_defines_a_typeclass

        def implements_interfaces(self) -> bool:
            return (len(self.state.asl) >= 2 
                and isinstance(self.second_child(), CLRList) 
                and self.second_child().type == "impls")

        def get_impls_asl(self) -> CLRList:
            return self.second_child()

        def get_implemented_interfaces(self) -> list[TypeClass]:
            interfaces = []
            if self.implements_interfaces():
                for child in self.get_impls_asl():
                    interfaces.append(self.state.get_module().get_typeclass_by_name(child.value))
                    # TODO: currently we only allow the interface to be looked up in the same
                    # module as the struct. In general, we need to allow interfaces from arbitrary
                    # modules.
            return interfaces

        def get_child_attribute_asls(self) -> list[CLRList]:
            return [child for child in self.state.asl if child.type == ":" or child.type == ":="]

        def get_child_attribute_names(self) -> list[str]:
            child_asls = self.get_child_attribute_asls()
            return [asl.first().value for asl in child_asls]




    class Interface(AbstractNodeInterface):
        asl_type = "interface"
        examples = """
        (interface name 
            (impls ...) 
            (: ...) 
            (: ...) 
        """
        _get_name = get_name_from_first_child
        get_interface_name = _get_name
        get_this_typeclass = get_typeclass_for_node_that_defines_a_typeclass

        def get_child_attribute_asls(self) -> list[CLRList]:
            return [child for child in self.state.asl if child.type == ":"]

        def get_child_attribute_names(self) -> list[str]:
            child_asls = self.get_child_attribute_asls()
            return [asl.first().value for asl in child_asls]

    class Def(AbstractNodeInterface):
        asl_type = "def"
        examples = """
        (def name
            (args ...)
            (rets ...)
            (seq ...))
        """
        get_function_name = get_name_from_first_child

    class Ilet(AbstractNodeInterface):
        asl_type = "ilet"
        examples = """
        1. (ilet name (call ...))
        2. (ilet name 4)
        3. (ilet name (<expression>))
        4. (ilet (tags ...) (tuple ...))
        5. (ilet (tags ...) (call ...))
        """
        def get_names() -> list[str]:
            pass

    class Let(AbstractNodeInterface):
        asl_type = "let"
        examples = """
        (let (: ...))
        """

    class Colon(AbstractNodeInterface):
        asl_type = ":"
        examples = """
        1. multiple assignment 
            (: (tags ...) (type ...))
        2. single_assignment
            (: name (type ...))
        """

        is_single_assignment = first_child_is_token

        def get_names(self) -> list[str]:
            if self.is_single_assignment():
                return [self.first_child().value]
            else:
                return [child.value for child in self.first_child()]

    class Assignment(AbstractNodeInterface):
        asl_type = "="
        examples = """
        1. single assignment 
            (= (ref name) 4)
        2. multiple assignment
            (= (tuple (ref name1) (ref name2)) (tuple 4 4))
        """

        is_single_assignment = first_child_is_token



