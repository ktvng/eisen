from __future__ import annotations

from alpaca.concepts import Type, Module
from alpaca.clr import CLRList, CLRToken
from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.common.eiseninstance import EisenFunctionInstance, EisenInstance
from eisen.validation.lookupmanager import LookupManager

class RefLike(AbstractNodeInterface):
    asl_types = ["ref", "::", ".", "fn"]

    def is_print(self) -> bool:
        return self.state.get_asl().type == "ref" and Ref(self.state).is_print()

    def is_append(self) -> bool:
        return self.state.get_asl().type == "fn" and Ref(self.state).is_append()

    def get_name(self) -> str:
        type = self.state.get_asl().type
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
        if self.state.get_asl().type == "::":
            return ModuleScope(self.state).get_module()
        return self.state.get_enclosing_module()

    def resolve_function_instance(self, argument_type: Type) -> EisenFunctionInstance:
        return LookupManager.resolve_function_reference_by_signature(
            name=self.get_name(),
            argument_type=argument_type,
            mod=self.get_module())

    def resolve_reference_type(self, argument_type: Type=None) -> Type | None:
        type = self.get_node_type()
        if type == "fn":
            return Fn(self.state).resolve_function_instance(argument_type).type
        elif type == "ref":
            return Ref(self.state).resolve_reference_type()
        elif type == "::":
            return ModuleScope(self.state).get_end_instance().type

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

    get_name = AbstractNodeInterface.get_name_from_first_child

    def resolve_function_instance(self, argument_type: Type) -> EisenFunctionInstance:
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

    def is_append(self) -> bool:
        return self.first_child().value == "append"


class Fn(AbstractNodeInterface):
    asl_type = "fn"
    examples = """
    (fn name)
    """
    get_name = AbstractNodeInterface.get_name_from_first_child

    def resolve_function_instance(self, argument_type: Type) -> EisenFunctionInstance:
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

    def get_instance(self) -> EisenInstance:
        return self.get_end_instance()

class Scope(AbstractNodeInterface):
    asl_type = "."
    examples = """
    (. (ref obj) attr)
    (. (. (ref obj) attr1) attr2)
    """

    def get_asl_defining_restriction(self) -> CLRList:
        return self.first_child()

    def get_attribute_name(self) -> str:
        return self.second_child().value

    def get_object_asl(self) -> CLRList:
        return self.first_child()

    def get_object_name(self) -> str:
        """
        Get the name of the parent object. For example, 'object.attribute' would
        return 'object'

        :return: Name of the parent object.
        :rtype: str
        """
        primary_asl = self.first_child()
        while primary_asl.type != "ref":
            primary_asl = primary_asl.first()
        return Ref(self.state.but_with(asl=primary_asl)).get_name()

    def get_full_name(self) -> str:
        primary_asl = self.state.get_asl()
        full_name = ""
        while primary_asl.type != "ref":
            full_name = Scope(self.state.but_with(asl=primary_asl)).get_attribute_name() + "." + full_name
            primary_asl = primary_asl.first()
        full_name = Ref(self.state.but_with(asl=primary_asl)).get_name() + "." + full_name
        return full_name[:-1]
