from __future__ import annotations

from alpaca.clr import CLRToken, CLRList
from alpaca.concepts._typeclass import TypeClass, Restriction2

from seer.common import Module
from seer.common.params import Params
from seer.common.restriction import Restriction


def get_name_from_first_child(self) -> str:
    return self.state.first_child().value

def first_child_is_token(self) -> bool:
    return isinstance(self.first_child(), CLRToken)

def get_typeclass_for_node_that_defines_a_typeclass(self) ->TypeClass:
    return self.state.get_enclosing_module().get_typeclass_by_name(self._get_name())


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

    class Mod(AbstractNodeInterface):
        asl_type = "mod"
        examples = """
        (mod name ...)
        """
        get_module_name = get_name_from_first_child
        def get_entered_module(self) -> Module:
            return self.state.get_node_data().enters_module

        def set_entered_module(self, mod: Module):
            self.state.get_node_data().enters_module = mod

        def enter_module_and_apply_fn_to_child_asls(self, fn):
            for child in self.state.asl[1:]:
                fn.apply(self.state.but_with(
                    asl=child,
                    mod=self.get_entered_module()))

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
                    interfaces.append(self.state.get_enclosing_module().get_typeclass_by_name(child.value))
                    # TODO: currently we only allow the interface to be looked up in the same
                    # module as the struct. In general, we need to allow interfaces from arbitrary
                    # modules.
            return interfaces

        def _get_embed_asls(self) -> list[CLRList]:
            return [child for child in self.state.asl if child.type == "embed"]

        def _parse_embed_asl_for_typeclasses(self, embed_asl: CLRList) -> list[TypeClass]:
            # TODO: currently we only allow the interface to be looked up in the same
            # module as the struct. In general, we need to allow interfaces from arbitrary
            # modules.
            if isinstance(embed_asl.first(), CLRList):
                return [self.state.get_enclosing_module().get_typeclass_by_name(child.value) for child in embed_asl.first()]
            return [self.state.get_enclosing_module().get_typeclass_by_name(embed_asl.first().value)]

        def get_embedded_structs(self) -> list[TypeClass]:
            embedded_structs: list[TypeClass] = []
            embed_asls = self._get_embed_asls()
            for asl in embed_asls:
                embedded_structs.extend(self._parse_embed_asl_for_typeclasses(asl))

            return embedded_structs

        def get_child_attribute_asls(self) -> list[CLRList]:
            return [child for child in self.state.asl if child.type == ":" or child.type == ":="]

        def get_child_attribute_names(self) -> list[str]:
            child_asls = self.get_child_attribute_asls()
            return [asl.first().value for asl in child_asls]

        def has_create_asl(self) -> bool:
            create_asls = [child for child in self.state.asl if child.type == "create"]
            return len(create_asls) == 1

        def get_create_asl(self) -> CLRList:
            create_asls = [child for child in self.state.asl if child.type == "create"]
            return create_asls[0]



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
        def get_args_asl(self) -> CLRList:
            return self.second_child()

        def get_rets_asl(self) -> CLRList:
            return self.third_child()


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

        # adds the struct name as the first parameter. this normalizes the structure
        # of (def ...) and (create ...) asls so we can use the same code to process
        # them
        def normalize(self, struct_name: str):
            self.state.asl._list.insert(0, CLRToken(type_chain=["TAG"], value=struct_name))
    
        def get_args_asl(self) -> CLRList:
            return self.second_child()

        def get_rets_asl(self) -> CLRList:
            return self.third_child()

    class CommonFunction(AbstractNodeInterface):
        asl_types = ["def", "create", ":="]
        examples = """
        (<asl_type> name
            (args ...)
            (rets ...)
            (seq ...))
        """
        get_name = get_name_from_first_child

        def get_args_asl(self) -> CLRList:
            return self.second_child()

        def get_rets_asl(self) -> CLRList:
            return self.third_child()

        def get_seq_asl(self) -> CLRList:
            return self.state.asl[-1]
 

    class Ilet(AbstractNodeInterface):
        asl_type = "ilet"
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

        def assigns_a_tuple(self) -> bool:
            return isinstance(self.first_child(), CLRList)

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

        def get_type_asl(self) -> CLRList:
            return self.second_child()

    class Assignment(AbstractNodeInterface):
        asl_type = "="
        examples = """
        1. single assignment 
            (= (ref name) 4)
        2. multiple assignment
            (= (tuple (ref name1) (ref name2)) (tuple 4 4))
        3. multiple call assignment
            (= (tuple (ref name1) (ref name2)) (call ...))
        """

        def is_single_assignment(self) -> bool:
            return first_child_is_token(self) or self.first_child().type != "tuple"

    class Fn(AbstractNodeInterface):
        asl_type = "fn"
        examples = """
        1. simple 
            (fn name)
        2. module
            (fn (:: mod name))
        3. attribute 
            (fn (. (ref obj) name))
        """
        
        def is_print(self) -> bool:
            return self.is_simple() and self.first_child().value == "print"

        def is_simple(self) -> bool:
            return isinstance(self.first_child(), CLRToken)

        def get_function_name(self) -> str:
            if self.is_simple():
                return self.state.first_child().value
            return self.first_child().second().value

        def get_function_type(self) -> TypeClass:
            return self.state.get_instances()[0].type
            

    class Ref(AbstractNodeInterface):
        asl_type = "ref"
        examples = """
        (ref name)
        """

        def get_restriction(self) -> Restriction:
            instance = self.state.get_node_data().instances[0]
            if instance.is_var:
                return Restriction.var
            else:
                return Restriction.let

        get_name = get_name_from_first_child

    class Scope(AbstractNodeInterface):
        asl_type = "."
        examples = """
        (. (ref obj) attr)
        """

        def get_asl_defining_restriction(self) -> CLRList:
            return self.first_child()

    class Call(AbstractNodeInterface):
        asl_type = "call"
        examples = """
        (call (fn ...) (params ... ))
        (call (:: mod (fn name)) (params ...)))))
        """

        def get_fn_asl(self) -> CLRList:
            if self.state.asl.type != "::" and self.state.asl.type != "fn":
                raise Exception(f"unexpected asl type of {self.state.asl.type}")
            if self.stateasl.type == "fn":
                return self.state.asl
            return self._unravel_scoping(asl=self.state.asl.second())

        def get_function_return_type(self) -> TypeClass:
            return self.state.get_node_data().returned_typeclass

        def get_argument_type(self) -> TypeClass:
            if self.first_child().type == "fn":
                node = Nodes.Fn(self.state.but_with(asl=self.first_child()))
            elif self.first_child().type == "::":
                node = Nodes.ModuleScope(self.state.but_with(asl=self.first_child()))
            return node.get_function_type().get_argument_type()

        def get_function_name(self) -> str:
            if self.first_child().type == "fn":
                node = Nodes.Fn(self.state.but_with(asl=self.first_child()))
            elif self.first_child().type == "::":
                node = Nodes.ModuleScope(self.state.but_with(asl=self.first_child()))
            return node.get_function_name()

        def is_print(self) -> str:
            node = Nodes.Fn(self.state.but_with(asl=self.first_child()))
            return node.is_print()

        def get_params_asl(self) -> str:
            return self.state.asl[-1]

    class ModuleScope(AbstractNodeInterface):
        asl_type = "::"
        examples = """
        (:: mod_name (disjoint_fn name))
        (:: outer (:: inner (disjoint_fn name)))
        """

        def get_function_type(self) -> TypeClass:
            working_mod = self.state.get_enclosing_module()
            next_asl = self.state.asl
            while next_asl.type == "::":
                # the name is stored as the CLRToken in the first position
                next_mod_name = next_asl.first().value
                working_mod = working_mod.get_child_by_name(next_mod_name)
                next_asl = next_asl.second()

            return working_mod.get_instance_by_name(name=self.get_function_name()).type

        def get_function_name(self) -> str:
            right_child = self.second_child()
            while right_child.type != "disjoint_fn":
                right_child = right_child.second()
            
            return right_child.first().value


    class Rets(AbstractNodeInterface):
        asl_type = "rets"
        examples = """
        (rets (: ...))
        (rets (prod_type ...))
        """

    class RawCall(AbstractNodeInterface):
        asl_type = "raw_call"
        examples = """
        (raw_call (ref name) (fn name) (params ...))
        (raw_call (ref name) (:: mod_name (disjoint_fn name)) (params ...))
        """

        def get_ref_asl(self) -> CLRList:
            return self.first_child()

        def get_fn_identifying_asl(self) -> CLRList:
            return self.second_child()

        def get_params_asl(self) -> CLRList:
            return self.third_child()

    class TypeLike(AbstractNodeInterface):
        asl_type = "type" 
        examples = """
        (type name)
        (var_type name)
        """
        get_name = get_name_from_first_child

        def get_restriction(self) -> Restriction2:
            if self.state.asl.type == "var_type":
                restriction = Restriction2.for_var()
            elif self.state.asl.type == "type":
                restriction = Restriction2.for_let()
            return restriction