from __future__ import annotations
from typing import Any

from alpaca.concepts._module import Module

class AbstractRestriction():
    pass

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
            mod: Module,
            components: list[TypeClass],
            component_names: list[str],
            inherits: list[TypeClass],
            embeds: list[TypeClass],
            restriction: AbstractRestriction):

        """a typeclass instance should only be created via the TypeclassFactory"""
        self.classification = classification 
        self.name = name
        self.mod = mod
        self.components = components
        self.component_names = component_names
        self.inherits = inherits
        self.embeds = embeds
        self.restriction = restriction 

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
        name_str = self.name if self.name else ""
        member_strs = [member._get_uuid_str() for member in self.components] 
        return self._get_module_prefix_for_uuid() + f"{name_str}({member_strs[0]} -> {member_strs[1]})" 


    # Return the uuid string which can be hashed to obtain a proper uuid. All 
    # typeclasses should be identified by uuid, such that muliple instances of 
    # the same typeclass can be created that express equality to each other. This
    # allows us to treat typeclasses as frozen literals.
    #
    # Restriction is not included in the uuid
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

    def get_uuid_str(self) -> str:
        return self._get_uuid_str()

    def get_direct_attribute_name_type_pairs(self) -> list[TypeClass]:
        return zip(self.component_names, self.components)

    def get_all_attribute_name_type_pairs(self) -> list[TypeClass]:
        pairs = self.get_direct_attribute_name_type_pairs()
        for embedded_type in self.embeds:
            pairs.extend(embedded_type.get_all_attribute_name_type_pairs())
        return pairs
    

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

    def is_tuple(self) -> bool:
        return self.classification == TypeClass.classifications.tuple

    def with_restriction(self, restriction: AbstractRestriction):
        return self._copy_with_restriction(restriction)

    def get_restrictions(self) -> list[AbstractRestriction]:
        if (self.classification == TypeClass.classifications.struct or self.classification == TypeClass.classifications.novel 
            or self.classification == TypeClass.classifications.interface):
            return [self.restriction]
        if self.classification == TypeClass.classifications.function:
            return self.get_return_type().get_restrictions()
        if self.classification == TypeClass.classifications.tuple:
            return [elem.restriction for elem in self.components]
        
        raise Exception(f"unhandled classification {self.classification}")

    def _copy_with_restriction(self, restriction: AbstractRestriction):
        return TypeClass(
            classification=self.classification,
            name=self.name,
            mod=self.mod,
            components=self.components,
            component_names=self.component_names,
            inherits=self.inherits,
            embeds=self.embeds,
            restriction=restriction)
