from __future__ import annotations

from typing import Any
from alpaca.concepts._module import Module
from copy import copy

class Type():
    class classifications:
        nil = "nil"
        novel = "novel"
        tuple = "tuple"
        function = "function"
        struct = "struct"
        interface = "interface"
        proto_struct = "proto_struct"
        proto_interface = "proto_interface"
        parametric = "parametric"

    def __init__(
            self,
            classification: str,
            name: str,
            mod: Module,
            components: list[Type],
            component_names: list[str],
            inherits: list[Type],
            embeds: list[Type],
            parametrics: list[Type],
            modifier: Any,
            parent_type: Type):

        """a type instance should only be created via the TypeclassFactory"""
        self.classification = classification
        self.name = name
        self.mod = mod
        self.components = components
        self.component_names = component_names
        self.inherits = inherits
        self.embeds = embeds
        self.parametrics = parametrics
        self.modifier = modifier
        self.parent_type = parent_type

    def delegated(self):
        raise Exception(f"Not implemented for {self}")

    # struct and novel types must be identified by the module they reside in and
    # their name. For novel types, this is required because we don't have any other
    # information to use. For struct types, this is required to avoid a circular
    # dependencies where some attribute of the struct may refer to that same struct.
    # Therefore we avoid consideration of the uuid for struct attributes, and
    # instead enforce the condition that a struct must be uniquely defined based
    # on it's name.

    def _get_module_prefix_for_uuid(self) -> str:
        mod_str = self.mod.get_full_name() if self.mod else ""
        return mod_str + "::" if mod_str else ""

    def _get_uuid_based_on_module_and_name(self) -> str:
        return self._get_module_prefix_for_uuid() + self.name

    def _get_uuid_based_on_components(self) -> str:
        name_str = self.name if self.name else ""
        member_strs = [member.get_uuid_str() for member in self.components]
        return self._get_module_prefix_for_uuid() + f"{name_str}({', '.join(member_strs)})"

    def _equiv(self, u : list, v : list) -> bool:
        return (u is not None
            and v is not None
            and len(u) == len(v)
            and all([x == y for x, y in zip(u, v)]))

    def __eq__(self, o: Any) -> bool:
        return hash(self) == hash(o)

    def __hash__(self) -> int:
        return hash(self.get_uuid_str())

    def __str__(self) -> str:
        return self.get_uuid_str()

    # Return the uuid string which can be hashed to obtain a proper uuid. All
    # types should be identified by uuid, such that multiple instances of
    # the same type can be created that express equality to each other. This
    # allows us to treat types as frozen literals.
    #
    # Restriction is not included in the uuid

    def get_direct_attribute_name_type_pairs(self) -> list[tuple[str, Type]]:
        return zip(self.component_names, self.components)

    def get_all_attribute_name_type_pairs(self) -> list[tuple[str, Type]]:
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

        return False

    def get_uuid_str(self) -> str: self.delegated()

    def finalize(self,
            components: list[Type],
            component_names: list[str],
            component_bindings: list[Any],
            inherits: list[Type] = None,
            embeds: list[Type] = None):
        self.delegated()


    def get_member_attribute_by_name(self, name: str) -> Type: self.delegated()
    def get_return_type(self) -> Type: self.delegated()
    def get_first_parameter_type(self) -> Type: self.delegated()
    def get_argument_type(self) -> Type: self.delegated()

    def is_function(self) -> bool: return False
    def is_struct(self) -> bool: return False
    def is_novel(self) -> bool: return False
    def is_tuple(self) -> bool: return False
    def is_nil(self) -> bool: return False

    def is_vec(self) -> bool:
        return self.classification == Type.classifications.parametric and self.name == "vec"

    def is_parametric(self) -> bool: return False
    def is_interface(self) -> bool: return False

    def unpack_into_parts(self):
        # TODO, move void to type
        if self.classification == Type.classifications.novel and self.name == "void":
            return []

        if self.classification == Type.classifications.tuple:
            return self.components
        return [self]

    def get_all_component_names(self) -> list[str]:
        """
        Return all component names, including those of embedded structs.
        """
        names = self.component_names.copy()
        for t in self.embeds:
            names += t.get_all_component_names()
        return names

    def with_modifier(self, modifier: Any) -> Type:
        new_type = copy(self)
        new_type.modifier = modifier
        return new_type

class FunctionType(Type):
    def __init__(self, name: str, mod: Module, arg: Type, ret: Type, modifier: Any = None):
        super().__init__(
            classification=Type.classifications.function,
            name=name,
            mod=mod,
            components=[arg, ret],
            component_names=["arg", "ret"],
            inherits=[],
            embeds=[],
            parametrics=[],
            modifier=modifier,
            parent_type=None)

    def get_uuid_str(self) -> str:
        name_str = self.name if self.name else ""
        member_strs = [member.get_uuid_str() for member in self.components]
        return self._get_module_prefix_for_uuid() + f"{name_str}({member_strs[0]} -> {member_strs[1]})"

    def is_function(self) -> bool:
        return True

    def get_return_type(self) -> Type:
        return self.components[1]

    def get_argument_type(self) -> Type:
        return self.components[0]

class _CompositeType(Type):
    def __init__(self, name: str, mod: Module, proto_cls: str, true_cls: str):
        self._is_proto = True
        self._true_classification = true_cls
        super().__init__(
            classification=proto_cls,
            name=name,
            mod=mod,
            components=[],
            component_names=[],
            inherits=[],
            embeds=[],
            parametrics=[],
            modifier=None,
            parent_type=None)

    def is_proto(self) -> bool:
        return self._is_proto

    def get_uuid_str(self) -> str:
        suffix = "<proto>" if self._is_proto else f"<{self.classification}>"
        return self._get_uuid_based_on_module_and_name() + suffix

    def get_member_attribute_by_name(self, name: str) -> Type:
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

    def finalize(self,
            components: list[Type],
            component_names: list[str],
            inherits: list[Type] = None,
            embeds: list[Type] = None):

        self.classification = self._true_classification
        self._is_proto = False
        self.components = components
        self.component_names = component_names
        if inherits: self.inherits = inherits
        if embeds: self.embeds = embeds

class TupleType(Type):
    def __init__(self, components: list[Type]):
        super().__init__(
            classification=Type.classifications.tuple,
            name="",
            mod=None,
            components=components,
            component_names=[],
            inherits=[],
            embeds=[],
            parametrics=[],
            modifier=None,
            parent_type=None)

    def get_uuid_str(self) -> str:
        return self._get_uuid_based_on_components()

    def is_tuple(self) -> bool:
        return True

class StructType(_CompositeType):
    def __init__(self, name: str, mod: Module):
        super().__init__(name, mod, Type.classifications.proto_struct, Type.classifications.struct)

    def is_struct(self) -> bool:
        return True

class InterfaceType(_CompositeType):
    def __init__(self, name: str, mod: Module):
        super().__init__(
            name,
            mod,
            Type.classifications.proto_interface,
            Type.classifications.interface)

    def is_interface(self) -> bool:
        return True

class NovelType(Type):
    def __init__(self, name: str, modifier: Any=None):
        super().__init__(
            classification=Type.classifications.novel,
            name=name,
            mod=None,
            components=[],
            component_names=[],
            inherits=[],
            embeds=[],
            parametrics=[],
            modifier=modifier,
            parent_type=None)

    def is_novel(self) -> bool:
        return True

    def get_uuid_str(self) -> str:
        return self._get_uuid_based_on_module_and_name()

class NilType(Type):
    def __init__(self):
        super().__init__(
            classification=Type.classifications.nil,
            name="nil",
            mod=None,
            components=[],
            component_names=[],
            inherits=[],
            embeds=[],
            parametrics=[],
            modifer=None,
            parent_type=None)

    def is_nil(self) -> bool:
        return True

    def get_uuid_str(self) -> str:
        return "nil"

class ParametricType(Type):
    def __init__(self, name: str, parametrics: list[Type], modifier: Any=None):
        super().__init__(
            classification=Type.classifications.parametric,
            name=name,
            mod=None,
            components=[],
            component_names=[],
            inherits=[],
            embeds=[],
            parametrics=parametrics,
            modifier=modifier,
            parent_type=None)

    def get_uuid_str(self) -> str:
        name_str = self.name if self.name else ""
        parametric_strs = [p.get_uuid_str() for p in self.parametrics]
        return self._get_module_prefix_for_uuid() + f"{name_str}[{', '.join(parametric_strs)}]"

    def get_first_parameter_type(self) -> Type:
        if self.classification != Type.classifications.parametric:
            raise Exception(f"Can only get_first_parameter_type on parametric constructions, got {self}")
        if not self.parametrics:
            raise Exception(f"self.parametrics is empty")
        return self.parametrics[0]
