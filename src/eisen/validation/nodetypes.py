from __future__ import annotations

from alpaca.clr import CLRToken, CLRList
from alpaca.concepts._type import Type
from alpaca.concepts._module import Module
from alpaca.concepts._typefactory import TypeFactory

from eisen.common import implemented_primitive_types
from eisen.common.eiseninstance import EisenInstance, EisenFunctionInstance
from eisen.common.state import State
from eisen.common.restriction import (GeneralRestriction, LetRestriction, VarRestriction,
    PrimitiveRestriction, NullableVarRestriction)

from eisen.validation.lookupmanager import LookupManager

def get_name_from_first_child(self) -> str:
    """assumes the first child is a token containing the name"""
    return self.state.first_child().value

def first_child_is_token(self) -> bool:
    """true if the first child is a CLRToken"""
    return isinstance(self.first_child(), CLRToken)

def get_type_for_node_that_defines_a_type(self) ->Type:
    """returns the type for either a struct/interface node which defines a type."""
    return self.state.get_enclosing_module().get_defined_type(self._get_name())

class Nodes():
    class AbstractNodeInterface():
        def __init__(self, state: State):
            self.state = state

        def first_child(self):
            return self.state.first_child()

        def second_child(self):
            return self.state.get_asl().second()

        def third_child(self):
            return self.state.get_asl().third()

        def get_line_number(self) -> int:
            return self.state.get_asl().line_number

        def get_node_type(self) -> str:
            return self.state.get_asl().type

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
            for child in self.state.get_asl()[1:]:
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
        get_this_type = get_type_for_node_that_defines_a_type

        def implements_interfaces(self) -> bool:
            return (len(self.state.get_asl()) >= 2
                and isinstance(self.second_child(), CLRList)
                and self.second_child().type == "impls")

        def get_impls_asl(self) -> CLRList:
            return self.second_child()

        def get_implemented_interfaces(self) -> list[Type]:
            interfaces = []
            if self.implements_interfaces():
                for child in self.get_impls_asl():
                    interfaces.append(self.state.get_defined_type(child.value))
                    # TODO: currently we only allow the interface to be looked up in the same
                    # module as the struct. In general, we need to allow interfaces from arbitrary
                    # modules.
            return interfaces

        def _get_embed_asls(self) -> list[CLRList]:
            return [child for child in self.state.get_asl() if child.type == "embed"]

        def _parse_embed_asl_for_types(self, embed_asl: CLRList) -> list[Type]:
            # TODO: currently we only allow the interface to be looked up in the same
            # module as the struct. In general, we need to allow interfaces from arbitrary
            # modules.
            if isinstance(embed_asl.first(), CLRList):
                return [self.state.get_defined_type(child.value) for child in embed_asl.first()]
            return [self.state.get_defined_type(embed_asl.first().value)]

        def get_embedded_structs(self) -> list[Type]:
            embedded_structs: list[Type] = []
            embed_asls = self._get_embed_asls()
            for asl in embed_asls:
                embedded_structs.extend(self._parse_embed_asl_for_types(asl))

            return embedded_structs

        def get_child_attribute_asls(self) -> list[CLRList]:
            return [child for child in self.state.get_asl() if child.type == ":" or child.type == ":="]

        def get_child_attribute_names(self) -> list[str]:
            child_asls = self.get_child_attribute_asls()
            return [asl.first().value for asl in child_asls]

        def has_create_asl(self) -> bool:
            create_asls = [child for child in self.state.get_asl() if child.type == "create"]
            return len(create_asls) == 1

        def get_create_asl(self) -> CLRList:
            create_asls = [child for child in self.state.get_asl() if child.type == "create"]
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
        get_this_type = get_type_for_node_that_defines_a_type

        def get_child_attribute_asls(self) -> list[CLRList]:
            return [child for child in self.state.get_asl() if child.type == ":"]

        def get_child_attribute_names(self) -> list[str]:
            child_asls = self.get_child_attribute_asls()
            return [asl.first().value for asl in child_asls]

    class Variant(AbstractNodeInterface):
        asl_type = "variant"
        examples = """
        (variant name
            (is ...)
            (@allow ...)
            (@deny ...))
        """
        _get_name = get_name_from_first_child
        get_variant_name = _get_name
        get_this_type = get_type_for_node_that_defines_a_type

        def get_token_defining_parent(self) -> CLRToken:
            return self.state.second_child()

        def get_parent_type(self) -> Type:
            parent_type_name = self.get_token_defining_parent().value
            return self.state.get_defined_type(parent_type_name)

        def get_is_asl(self) -> CLRList:
            for child in self.state.get_child_asls():
                if child.type == "is_fn":
                    return child
            raise Exception(f"expected an 'is_fn' asl for variant: {self.get_variant_name()}")


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

        def get_seq_asl(self) -> CLRList:
            return self.state.asl[-1]

        def get_arg_names(self) -> list[str]:
            return Nodes.Def._unpack_to_get_names(self.get_args_asl())

        def get_ret_names(self) -> list[str]:
            return Nodes.Def._unpack_to_get_names(self.get_rets_asl())

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
            return self.state.get_asl()[-1]

        def enter_context_and_apply_fn(self, fn) -> None:
            # must create fn_context here as it is shared by all children
            fn_context = self.state.create_block_context("func")
            will_enter_constructor = self.state.asl.type == "create"
            for child in self.state.get_child_asls():
                fn.apply(self.state.but_with(
                    asl=child,
                    context=fn_context,
                    inside_constructor=will_enter_constructor))

    class Is(AbstractNodeInterface):
        asl_type = "is"
        examples = """
        (is (expr ...) TAG)
        """

        def get_type_name(self) -> str:
            return self.second_child().value

        def get_considered_type(self) -> Type:
            return self.state.get_defined_type(self.get_type_name())

        def _get_name_of_is_function(self) -> str:
            return "is_" + self.get_type_name()

        def _get_type_of_is_function(self) -> Type:
            parent_type = self.get_considered_type().parent_type
            # TODO: function types should not need modules
            return TypeFactory.produce_function_type(parent_type, self.state.get_bool_type(), mod=None)

        def get_is_function_instance(self) -> EisenFunctionInstance:
            LookupManager.resolve_function_reference_type_by_signature(
                name=self._get_name_of_is_function(),
                type=self._get_type_of_is_function(),
                mod=self.state.get_enclosing_module())


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

        def assigns_a_tuple(self) -> bool:
            return isinstance(self.first_child(), CLRList)

        def unpack_assigned_types(self, type: Type) -> list[Type]:
            """if the assigned type is a tuple, unpack the components of the tuple
            into a list of component types; otherwise returns a list with the singluar
            type as the only member"""
            if self.assigns_a_tuple():
                return type.components
            else:
                return [type]

        def get_restriction(self) -> GeneralRestriction:
            if self.state.asl.type == "ilet":
                return LetRestriction()
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
        is_single_assignment = first_child_is_token

        def get_restriction(self) -> GeneralRestriction:
            if self.get_node_type() == "var":
                return VarRestriction()
            elif self.get_node_type() == "var?":
                return NullableVarRestriction()
            return None

        def get_is_nullable(self) -> bool:
            return self.get_node_type() == "var?"

        def get_is_var(self) -> bool:
            node_type = self.get_node_type()
            return node_type == "var" or node_type == "var?"


        def get_names(self) -> list[str]:
            if self.is_single_assignment():
                return [self.first_child().value]
            else:
                return [child.value for child in self.first_child()]

        def get_type_asl(self) -> CLRList:
            return self.second_child()

    class CompoundAssignment(AbstractNodeInterface):
        asl_types = ["+=", "-=", "*=", "/="]
        examples = """
        (+= (ref a) 4)
        (-= (. (ref b) c) (+ 4 9))
        """
        def get_arithmetic_operation(self) -> str:
            return self.state.get_asl().type[0]

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

    class RefLike(AbstractNodeInterface):
        asl_types = ["ref", "::", "."]

        def is_print(self) -> bool:
            return self.state.get_asl().type == "ref" and Nodes.Ref(self.state).is_print()

        def get_name(self) -> str:
            type = self.state.get_asl().type
            if type == "ref":
                return Nodes.Ref(self.state).get_name()
            elif type == "::":
                return Nodes.ModuleScope(self.state).get_end_name()
            elif type == ".":
                return Nodes.Scope(self.state).get_attribute_name()

            raise Exception("unknown type")

        def get_module(self):
            if self.state.get_asl().type == "::":
                return Nodes.ModuleScope(self.state).get_module()
            return self.state.get_enclosing_module()

        def resolve_function_instance(self, argument_type: Type) -> EisenFunctionInstance:
            return LookupManager.resolve_function_reference_by_signature(
                name=self.get_name(),
                argument_type=argument_type,
                mod=self.get_module())

        def resolve_instance(self) -> EisenInstance:
            return LookupManager.resolve_reference(
                name=self.get_name(),
                context=self.state.get_context(),
                mod=self.get_module())

        def assign_instance(self, instance: EisenInstance):
            type = self.state.get_asl().type
            if  type == "ref" or type == "::":
                self.state.assign_instances(instance)

    class Ref(AbstractNodeInterface):
        asl_type = "ref"
        examples = """
        (ref name)
        """

        def get_name(self) -> str:
            return self.first_child().value

        def resolve_function_instance(self, argument_type: Type) -> EisenFunctionInstance:
            return LookupManager.resolve_function_reference_by_signature(
                name=self.get_name(),
                argument_type=argument_type,
                mod=self.get_module())

        def resolve_reference_type(self) -> Type:
            return LookupManager.resolve_reference_type(
                name=self.get_name(),
                context=self.state.get_context(),
                mod=self.state.get_enclosing_module(),
                argument_type=self.state.get_arg_type())

        def resolve_instance(self) -> EisenInstance:
            return LookupManager.resolve_reference(
                name=self.get_name(),
                context=self.state.get_context(),
                mod=self.state.get_enclosing_module(),
                argument_type=self.state.get_arg_type())

        def get_module(self):
            return self.state.get_enclosing_module()

        def get_type(self) -> Type:
            return self.state.get_returned_type()

        def is_print(self) -> bool:
            return self.first_child().value == "print"

    class Scope(AbstractNodeInterface):
        asl_type = "."
        examples = """
        (. (ref obj) attr)
        """

        def get_asl_defining_restriction(self) -> CLRList:
            return self.first_child()

        def get_attribute_name(self) -> str:
            return self.second_child().value

        def get_object_asl(self) -> CLRList:
            return self.first_child()

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
            return Nodes.RefLike(self.state.but_with_first_child()).get_name()

        def get_function_return_restrictions(self) -> list[GeneralRestriction]:
            return self.get_function_return_type().get_restrictions()

        def is_print(self) -> str:
            node = Nodes.RefLike(self.state.but_with(asl=self.first_child()))
            return node.is_print()

        def get_params_asl(self) -> str:
            return self.state.get_asl()[-1]

        def get_params(self) -> list[CLRList]:
            return self.get_params_asl()._list

        def get_param_names(self) -> list[str]:
            return Nodes.Def(self.state.but_with(asl=self.get_asl_defining_the_function())).get_arg_names()

        def get_return_names(self) -> list[str]:
            return Nodes.Def(self.state.but_with(asl=self.get_asl_defining_the_function())).get_ret_names()

        def get_asl_defining_the_function(self) -> CLRList:
            return self.state.but_with_first_child().get_instances()[0].asl

    class ModuleScope(AbstractNodeInterface):
        asl_type = "::"
        examples = """
        (:: mod_name name))
        (:: outer (:: inner name)))
        """

        def get_module_name(self) -> str:
            return self.first_child().value

        def _follow_chain(self, asl: CLRList) -> list[str]:
            if isinstance(asl, CLRToken):
                return [asl.value]

            lst = self._follow_chain(asl.first())
            lst.append(asl.second().value)
            return lst

        def _unpack_structure(self) -> tuple[str, list[str]]:
            end = self.second_child().value
            return end, self._follow_chain(self.first_child())

        def get_end_instance(self) -> EisenInstance:
            end, mods = self._unpack_structure()
            current_mod = self.state.get_enclosing_module()
            for mod_name in mods:
                current_mod = current_mod.get_child_by_name(mod_name)

            instance = current_mod.get_instance(end)
            if instance is None:
                instances = current_mod.get_all_function_instances_with_name(end)
                return instances[0]
            return instance

        def get_end_name(self) -> str:
            end, _ = self._unpack_structure()
            return end

        def get_module(self) -> Module:
            _, mods = self._unpack_structure()
            current_mod = self.state.get_enclosing_module()
            for mod_name in mods:
                current_mod = current_mod.get_child_by_name(mod_name)
            return current_mod

    class ArgsRets(AbstractNodeInterface):
        asl_types = ["rets", "args"]
        examples = """
        (rets (: ...))
        (rets (prod_type ...))
        """

        def get_names(self) -> list[str]:
            if self.state.asl.has_no_children():
                return []
            if self.first_child().type == ":":
                return Nodes.Decl(self.state.but_with_first_child()).get_names()
            return [Nodes.Decl(self.state.but_with(asl=child)).get_names()[0] for child in self.first_child()]

        def convert_let_args_to_var(self, type: Type):
            """For function arguments, if the declared type is unspecified, we should
            convert this to let types for structs"""
            if self.get_node_type() == "args":
                if type.is_tuple():
                    for component in type.components:
                        if component.is_struct():
                            component.restriction = VarRestriction()
                elif type.is_struct():
                    type.restriction = VarRestriction()


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

    class TypeLike(AbstractNodeInterface):
        asl_type = "type"
        examples = """
        (type name)
        (var_type name)
        """
        get_name = get_name_from_first_child

        def get_restriction(self, type: Type) -> GeneralRestriction:
            # var takes precedence over primitive
            if self.get_node_type() == "var_type":
                return VarRestriction()
            elif self.get_node_type() == "var_type?":
                return NullableVarRestriction()

            if type.classification == Type.classifications.variant:
                return VarRestriction()

            if self.state.get_asl().first().value in implemented_primitive_types:
                restriction = PrimitiveRestriction()
            elif self.state.get_asl().type == "type":
                restriction = LetRestriction()
            return restriction
