from __future__ import annotations
from typing import Any

from alpaca.concepts._module import Module

class AbstractRestriction():
    pass

# TODO: figure this out
class FunctionSignature():
    def __init__(self, name: str, type: Type):
        self.name = name
        self.type = type

class VariantAcl():
    def __init__(self, allowed_attrs: list[str], allowed_fns: list[FunctionSignature]):
        self.allowed_attrs = []
        self.allowed_fns = [FunctionSignature]

class Type():
    class classifications:
        nil = "nil"
        novel = "novel"
        tuple = "tuple"
        function = "function"
        struct = "struct"
        interface = "interface"
        variant = "variant"
        proto_struct = "proto_struct"
        proto_interface = "proto_interface"
        proto_variant = "proto_variant"

    def __init__(
            self,
            classification: str,
            name: str,
            mod: Module,
            components: list[Type],
            component_names: list[str],
            inherits: list[Type],
            embeds: list[Type],
            restriction: AbstractRestriction,
            parent_type: Type):

        """a type instance should only be created via the TypeclassFactory"""
        self.classification = classification
        self.name = name
        self.mod = mod
        self.components = components
        self.component_names = component_names
        self.inherits = inherits
        self.embeds = embeds
        self.restriction = restriction
        self.parent_type = parent_type

    def finalize(self,
            components: list[Type],
            component_names: list[str],
            inherits: list[Type] = [],
            embeds: list[Type] = []):
        if (self.classification != Type.classifications.proto_interface and
            self.classification != Type.classifications.proto_struct):
            raise Exception("can only finalize a proto* Type")

        if self.classification == Type.classifications.proto_interface:
            self.classification = Type.classifications.interface
        elif self.classification == Type.classifications.proto_struct:
            self.classification = Type.classifications.struct

        self.components = components
        self.component_names = component_names
        self.inherits = inherits
        self.embeds = embeds

    def finalize_variant(self, parent_type: Type):
        self.classification = Type.classifications.variant
        self.parent_type = parent_type
        self.inherits = []
        self.embeds = []
        self.components = []

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
    # types should be identified by uuid, such that muliple instances of
    # the same type can be created that express equality to each other. This
    # allows us to treat types as frozen literals.
    #
    # Restriction is not included in the uuid
    def _get_uuid_str(self) -> str:
        if self.classification == Type.classifications.novel:
            return self._get_uuid_based_on_module_and_name()
        elif self.classification == Type.classifications.struct:
            return self._get_uuid_based_on_module_and_name() + "<struct>"
        elif self.classification == Type.classifications.interface:
            return self._get_uuid_based_on_module_and_name() + "<interface>"
        elif self.classification == Type.classifications.tuple:
            return self._get_uuid_based_on_components()
        elif self.classification == Type.classifications.function:
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
        # TODO: this is an implementation dependency
        nilable = " var?" if self.restriction and self.restriction.is_nullable() else ""
        return self._get_uuid_str() + nilable

    def get_uuid_str(self) -> str:
        return self._get_uuid_str()

    def get_direct_attribute_name_type_pairs(self) -> list[Type]:
        return zip(self.component_names, self.components)

    def get_all_attribute_name_type_pairs(self) -> list[Type]:
        pairs = self.get_direct_attribute_name_type_pairs()
        for embedded_type in self.embeds:
            pairs.extend(embedded_type.get_all_attribute_name_type_pairs())
        return pairs


    def has_member_attribute_with_name(self, name: str) -> bool:
        if name in self.component_names:
            return True

        # struct may also have embedded structs
        if self.classification == Type.classifications.struct:
            for type in self.embeds:
                if type.has_member_attribute_with_name(name):
                    return True

        if self.classification == Type.classifications.variant:
            return self.parent_type.has_member_attribute_with_name(name)

        return False

    def get_member_attribute_by_name(self, name: str) -> Type:
        if self.classification == Type.classifications.variant:
            return self.parent_type.get_member_attribute_by_name(name)

        if self.classification != Type.classifications.struct and self.classification != Type.classifications.interface:
            raise Exception(f"Can only get_member_attribute_by_name on struct constructions, got {self}")

        if name not in self.component_names:
            if self.classification == Type.classifications.struct:
                matching_embeddings = [tc for tc in self.embeds if tc.has_member_attribute_with_name(name)]
                if len(matching_embeddings) != 1:
                    raise Exception(f"bad embedding structure, need to be handled elswhere got {len(matching_embeddings)} matches, need 1")
                if matching_embeddings:
                    return matching_embeddings[0].get_member_attribute_by_name(name)

            raise Exception(f"Type {self} does not have member attribute named '{name}'")

        pos = self.component_names.index(name)
        return self.components[pos]

    def get_return_type(self) -> Type:
        if self.classification != Type.classifications.function:
            raise Exception(f"Can only get_return_type on function constructions, got {self}")

        return self.components[1]

    def get_argument_type(self) -> Type:
        if self.classification != Type.classifications.function:
            raise Exception(f"Can only get_argument_type on function constructions, got {self}")

        return self.components[0]

    def is_function(self) -> bool:
        return self.classification == Type.classifications.function

    def is_struct(self) -> bool:
        return self.classification == Type.classifications.struct

    def is_novel(self) -> bool:
        return self.classification == Type.classifications.novel

    def is_tuple(self) -> bool:
        return self.classification == Type.classifications.tuple

    def is_nil(self) -> bool:
        return self.classification == Type.classifications.nil

    def with_restriction(self, restriction: AbstractRestriction = None):
        # A tuple should not have restrictions, but should have restrictions passed
        # to each component
        if self.is_tuple() and restriction is not None:
            new_type = self._copy_with_restriction(None)
            new_type.components = [t._copy_with_restriction(restriction) for t in new_type.components]
            return new_type

        if restriction is not None:
            return self._copy_with_restriction(restriction)
        return self

    def unpack_into_parts(self):
        if (self.classification == Type.classifications.struct or self.classification == Type.classifications.novel
            or self.classification == Type.classifications.interface):
            return [self]
        if self.classification == Type.classifications.function:
            return self.get_return_type().unpack_into_parts()
        if self.classification == Type.classifications.tuple:
            return self.components
        if self.classification == Type.classifications.variant:
            return [self]

        raise Exception(f"unhandled classification {self.classification}")

    def get_restrictions(self) -> list[AbstractRestriction]:
        if (self.classification == Type.classifications.struct or self.classification == Type.classifications.novel
            or self.classification == Type.classifications.interface):
            return [self.restriction]
        if self.classification == Type.classifications.function:
            return self.get_return_type().get_restrictions()
        if self.classification == Type.classifications.tuple:
            return [elem.restriction for elem in self.components]
        if self.classification == Type.classifications.variant:
            return [self.restriction]

        raise Exception(f"unhandled classification {self.classification}")

    def _copy_with_restriction(self, restriction: AbstractRestriction):
        return Type(
            classification=self.classification,
            name=self.name,
            mod=self.mod,
            components=self.components,
            component_names=self.component_names,
            inherits=self.inherits,
            embeds=self.embeds,
            restriction=restriction,
            parent_type=self.parent_type)
