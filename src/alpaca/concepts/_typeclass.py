from __future__ import annotations
from typing import Any

from alpaca.concepts._context import Context

class TypeClass():
    class classifications:
        novel = "novel"
        tuple = "tuple"
        function = "function"
        struct = "struct"
        interface = "interface"
        proto_struct = "proto_struct"
        proto_interface = "proto_interface"

    def __init__(
            self,
            classification: str,
            name: str,
            mod: Context,
            components: list[TypeClass],
            component_names: list[str],
            inherits: list[TypeClass],
            embeds: list[TypeClass]):

        self.classification = classification 
        self.name = name
        self.mod = mod
        self.components = components
        self.component_names = component_names
        self.inherits = inherits
        self.embeds =embeds

    def finalize(self, 
            components: list[TypeClass], 
            component_names: list[str], 
            inherits: list[TypeClass] = [],
            embeds: list[TypeClass] = []):
        if (self.classification != TypeClass.classifications.proto_interface and
            self.classification != TypeClass.classifications.proto_struct):
            raise Exception("can only finalize a proto* TypeClass")

        if self.classification == TypeClass.classifications.proto_interface:
            self.classification = TypeClass.classifications.interface
        elif self.classification == TypeClass.classifications.proto_struct:
            self.classification = TypeClass.classifications.struct

        self.components = components 
        self.component_names = component_names
        self.inherits = inherits
        self.embeds = embeds

    def _get_module_prefix_for_uuid(self) -> str:
        mod_str = self.mod.get_full_name() if self.mod else ""
        return mod_str + "::" if mod_str else ""


    # struct and novel types must be identified by the module they reside in and 
    # their name. For novel types, this is required because we don't have any other
    # information to use. For struct types, this is required to avoid a circular
    # dependencies where some attribute of the struct may refer to that same struct.
    # Therefore we avoid consideration of the uuid for struct attributes, and 
    # instead enforce the condition that a struct must be uniquely defined based
    # on it's name.
    def _get_uuid_based_on_module_and_name(self) -> str:
        return self._get_module_prefix_for_uuid() + self.name

    def _get_uuid_based_on_components(self) -> str:
        name_str = self.name if self.name else ""
        member_strs = [member._get_uuid_str() for member in self.components] 
        return self._get_module_prefix_for_uuid() + f"{name_str}({', '.join(member_strs)})" 

    def _get_uuid_for_function(self) -> str:
        name_str = self.name if self.name else "f"
        member_strs = [member._get_uuid_str() for member in self.components] 
        return self._get_module_prefix_for_uuid() + f"{name_str}({member_strs[0]} -> {member_strs[1]})" 


    # Return the uuid string which can be hashed to obtain a proper uuid. All 
    # typeclasses should be identified by uuid, such that muliple instances of 
    # the same typeclass can be created that express equality to each other. This
    # allows us to treat typeclasses as frozen literals.
    def _get_uuid_str(self) -> str:
        if self.classification == TypeClass.classifications.novel:
            return self._get_uuid_based_on_module_and_name()
        elif self.classification == TypeClass.classifications.struct:
            return self._get_uuid_based_on_module_and_name() + "<struct>"
        elif self.classification == TypeClass.classifications.interface:
            return self._get_uuid_based_on_module_and_name() + "<interface>"
        elif self.classification == TypeClass.classifications.tuple:
            return self._get_uuid_based_on_components()
        elif self.classification == TypeClass.classifications.function:
            return self._get_uuid_for_function()
        else:
            # this should be the case for proto entities,
            return self._get_uuid_based_on_module_and_name()

    def _equiv(self, u : list, v : list) -> bool:
        return (u is not None 
            and v is not None 
            and len(u) == len(v) 
            and all([x == y for x, y in zip(u, v)]))

    def __eq__(self, o: Any) -> bool:
        return hash(self) == hash(o)

    def __hash__(self) -> int:
        return hash(self._get_uuid_str())
        
    def __str__(self) -> str:
        return self._get_uuid_str()

    def has_member_attribute_with_name(self, name: str) -> bool:
        if name in self.component_names:
            return True

        # struct may also have embedded structs
        if self.classification == TypeClass.classifications.struct:
            for typeclass in self.embeds:
                if typeclass.has_member_attribute_with_name(name):
                    return True
        return False
            


    def get_member_attribute_by_name(self, name: str) -> TypeClass:
        if self.classification != TypeClass.classifications.struct and self.classification != TypeClass.classifications.interface:
            raise Exception(f"Can only get_member_attribute_by_name on struct constructions, got {self}")

        if name not in self.component_names:
            if self.classification == TypeClass.classifications.struct:
                matching_embeddings = [tc for tc in self.embeds if tc.has_member_attribute_with_name(name)]
                if len(matching_embeddings) != 1:
                    raise Exception(f"bad embedding structure, need to be handled elswhere got {len(matching_embeddings)} matches, need 1")
                if matching_embeddings:
                    return matching_embeddings[0].get_member_attribute_by_name(name)

            raise Exception(f"Type {self} does not have member attribute named '{name}'")

        pos = self.component_names.index(name)
        return self.components[pos]

    def get_return_type(self) -> TypeClass:
        if self.classification != TypeClass.classifications.function:
            raise Exception(f"Can only get_return_type on function constructions, got {self}")
        
        return self.components[1]

    def get_argument_type(self) -> TypeClass:
        if self.classification != TypeClass.classifications.function:
            raise Exception(f"Can only get_argument_type on function constructions, got {self}")
        
        return self.components[0]

    def is_function(self) -> bool:
        return self.classification == TypeClass.classifications.function

    def is_struct(self) -> bool:
        return self.classification == TypeClass.classifications.struct

    def is_novel(self) -> bool:
        return self.classification == TypeClass.classifications.novel 


class TypeClassFactory():
    @classmethod
    def produce_novel_type(cls, name: str, global_mod: Context) -> TypeClass:
        return TypeClass(
            classification=TypeClass.classifications.novel, 
            name=name, 
            mod=global_mod, 
            components=[], 
            component_names=[], 
            inherits=[],
            embeds=[])

    @classmethod
    def produce_tuple_type(cls, components: list[TypeClass], global_mod: Context) -> TypeClass:
        return TypeClass(
            classification=TypeClass.classifications.tuple, 
            name="",
            mod=global_mod, 
            components=components, 
            component_names=[], 
            inherits=[],
            embeds=[])

    @classmethod
    def produce_function_type(cls, arg: TypeClass, ret: TypeClass, mod: Context, name: str = "") -> TypeClass:
        return TypeClass(
            classification=TypeClass.classifications.function, 
            name=name, 
            mod=mod, 
            components=[arg, ret], 
            component_names=["arg", "ret"], 
            inherits=[],
            embeds=[])

    @classmethod
    def produce_proto_struct_type(cls, name: str, mod: Context) -> TypeClass:
        return TypeClass(
            classification=TypeClass.classifications.proto_struct,
            name=name, 
            mod=mod, 
            components=[], 
            component_names=[], 
            inherits=[],
            embeds=[])

    @classmethod
    def produce_proto_interface_type(cls, name: str, mod: Context) -> TypeClass:
        return TypeClass(
            classification=TypeClass.classifications.proto_interface, 
            name=name, 
            mod=mod, 
            components=[], 
            component_names=[], 
            inherits=[],
            embeds=[])
