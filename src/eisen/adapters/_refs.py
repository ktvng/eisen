from __future__ import annotations

from alpaca.concepts import Type, Module
from alpaca.clr import AST, ASTToken
from eisen.common.traits import TraitImplementation
from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.common.eiseninstance import FunctionInstance, Instance
from eisen.validation.lookupmanager import LookupManager
from eisen.state.basestate import BaseState

class RefLike(AbstractNodeInterface):
    ast_types = ["ref", "::", ".", "fn"]

    def is_print(self) -> bool:
        return self.state.get_ast().type == "ref" and Ref(self.state).is_print()

    def is_append(self) -> bool:
        return self.state.get_ast().type == "fn" and Ref(self.state).is_append()

    def get_name(self) -> str:
        type = self.state.get_ast().type
        if type == "ref":
            return Ref(self.state).get_name()
        elif type == "::":
            return ModuleScope(self.state).get_end_name()
        elif type == ".":
            return Scope(self.state).get_attribute_name()
        elif type == "fn":
            return Fn(self.state).get_name()

        raise Exception(f"unknown type {type}")

    def get_module(self):
        if self.state.get_ast().type == "::":
            return ModuleScope(self.state).get_module()
        return self.state.get_enclosing_module()

    def resolve_function_instance(self, argument_type: Type) -> FunctionInstance:
        return LookupManager.resolve_function_reference_by_signature(
            name=self.get_name(),
            argument_type=argument_type,
            mod=self.get_module())

    def resolve_reference_type(self, argument_type: Type=None) -> Type | None:
        match self.get_ast_type():
            case "fn":
                return Fn(self.state).resolve_function_instance(argument_type).type
            case "ref":
                return Ref(self.state).resolve_reference_type()
            case "::":
                return ModuleScope(self.state).get_end_instance().type
            case ".":
                return Scope(self.state).get_end_type()

    def resolve_instance(self) -> Instance:
        return LookupManager.resolve_reference(
            name=self.get_name(),
            context=self.state.get_context(),
            mod=self.get_module())

    def assign_instance(self, instance: Instance):
        type = self.state.get_ast().type
        if  type == "ref" or type == "::":
            self.state.assign_instances(instance)


class Ref(AbstractNodeInterface):
    ast_type = "ref"
    examples = """
    (ref name)
    """

    get_name = AbstractNodeInterface.get_name_from_first_child

    def resolve_function_instance(self, argument_type: Type) -> FunctionInstance:
        return LookupManager.resolve_function_reference_by_signature(
            name=self.get_name(),
            argument_type=argument_type,
            mod=self.get_module())

    def resolve_reference_type(self) -> Type | None:
        return LookupManager.resolve_reference_type(
            name=self.get_name(),
            context=self.state.get_context(),
            mod=self.state.get_enclosing_module(),
            argument_type=self.state.get_arg_type())

    def resolve_instance(self) -> Instance:
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

    def is_append(self) -> bool:
        return self.first_child().value == "append"


class Fn(AbstractNodeInterface):
    ast_type = "fn"
    examples = """
    (fn name)
    """
    get_name = AbstractNodeInterface.get_name_from_first_child

    def resolve_function_instance(self, argument_type: Type) -> FunctionInstance:
        if argument_type:
            return LookupManager.resolve_function_reference_by_signature(
                name=self.get_name(),
                argument_type=argument_type,
                mod=self.state.get_enclosing_module())
        else:
            instances = LookupManager.resolve_function_references_by_name(
                name=self.get_name(),
                mod=self.state.get_enclosing_module())
            if len(instances) == 1:
                return instances[0]
            # TODO: raise compiler message here

class ModuleScope(AbstractNodeInterface):
    ast_type = "::"
    examples = """
    (:: mod_name name))
    (:: outer (:: inner name)))
    """

    def get_module_name(self) -> str:
        return self.first_child().value

    def _follow_chain(self, ast: AST) -> list[str]:
        if isinstance(ast, ASTToken):
            return [ast.value]

        lst = self._follow_chain(ast.first())
        lst.append(ast.second().value)
        return lst

    def _unpack_structure(self) -> tuple[str, list[str]]:
        end = self.second_child().value
        return end, self._follow_chain(self.first_child())

    def get_end_instance(self) -> Instance:
        end, mods = self._unpack_structure()
        current_mod = self.state.get_enclosing_module()
        for mod_name in mods:
            current_mod = current_mod.get_child_by_name(mod_name)

        instance = current_mod.get_obj("instance", end)
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

    def get_instance(self) -> Instance:
        return self.get_end_instance()

class Scope(AbstractNodeInterface):
    ast_type = "."
    examples = """
    (. (ref obj) attr)
    (. (. (ref obj) attr1) attr2)
    (. (cast (ref obj) (type into_type)) attr)
    (. (call (fn f) (params ...)) attr)
    """

    def get_ast_defining_restriction(self) -> AST:
        return self.first_child()

    def get_attribute_name(self) -> str:
        return self.second_child().value

    def get_object_ast(self) -> AST:
        return self.first_child()

    def get_object_name(self) -> str:
        """
        Get the name of the parent object. For example, 'object.attribute' would
        return 'object'

        :return: Name of the parent object.
        :rtype: str
        """
        primary_ast = self.first_child()
        while primary_ast.type != "ref":
            primary_ast = primary_ast.first()
        return Ref(self.state.but_with(ast=primary_ast)).get_name()

    def get_full_name(self) -> str:
        primary_ast = self.state.get_ast()
        full_name = ""
        while primary_ast.type != "ref":
            full_name = Scope(self.state.but_with(ast=primary_ast)).get_attribute_name() + "." + full_name
            primary_ast = primary_ast.first()
        full_name = Ref(self.state.but_with(ast=primary_ast)).get_name() + "." + full_name
        return full_name[:-1]

    @staticmethod
    def _get_end_type(state: BaseState) -> Type:
        match state.get_ast_type():
            case ".":
                return Scope._get_end_type(state.but_with_first_child())\
                            .get_member_attribute_by_name(Scope(state).get_attribute_name())
            case "ref": return Ref(state).resolve_reference_type()
            # Can't use Cast() because we're pre-typechecker
            case "cast": return state.but_with_second_child().get_node_data().returned_type
            case "call": return state.but_with_first_child().get_node_data().returned_type.get_return_type()


    def get_end_type(self) -> Type:
        return Scope._get_end_type(self.state)

    def get_parent_type(self) -> Type:
        return self.state.but_with_first_child().get_returned_type()

class Cast(AbstractNodeInterface):
    ast_type = "cast"
    examples = """
    (cast (ref obj) (type otherObj))
    """

    def get_cast_into_type(self) -> Type:
        return self.state.but_with_second_child().get_returned_type()

    def get_original_type(self) -> Type:
        return self.state.but_with_first_child().get_returned_type()

    def get_trait_implementation(self) -> TraitImplementation:
        return self.state.get_enclosing_module().get_obj(
            container_name="trait_implementations",
            name=TraitImplementation.get_key(self.get_cast_into_type(), self.get_original_type()))
