from __future__ import annotations
from typing import Any

import uuid

from alpaca.concepts._type import Type
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
            inherits: list[TypeClass]):

        self.classification = classification 
        self.name = name
        self.mod = mod
        self.components = components
        self.component_names = component_names
        self.inherits = inherits

    def finalize(self, components: list[TypeClass], component_names: list[str], inherits: list[TypeClass] = []):
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

    def _get_uuid_str(self) -> str:
        mod_str = self.mod.get_full_name() if self.mod else ""
        if self.classification == TypeClass.classifications.novel:
            return mod_str + "::" + self.name

        name_str = self.name if self.name else ""

        if self.component_names:
            member_strs = [f"{member_name}:{member._get_uuid_str()}" 
                for member_name, member in zip(self.component_names, self.components)]
        else:
            member_strs = [member._get_uuid_str() for member in self.components] 

        return mod_str + "::" + f"{name_str}={self.classification}({', '.join(member_strs)})" 

    # note: we omit the global module for brevity. thus global::int => int
    def _get_printable_str(self, shorten: bool = False) -> str:
        mod_str = self.mod.get_full_name() if self.mod else ""
        mod_str = mod_str + "::" if mod_str else ""
        if self.classification == TypeClass.classifications.novel:
            return mod_str + self.name

        if shorten and self.name:
            return self.name

        name_str = self.name if self.name else ""

        if self.classification == TypeClass.classifications.function:
            arg = self.components[0]._get_printable_str(shorten=True)
            ret = self.components[1]._get_printable_str(shorten=True)
            return mod_str + f"{name_str}<{self.classification}({arg} -> {ret})>"

        if self.component_names:
            member_strs = [f"{member_name}:{member._get_printable_str(shorten=True)}" 
                for member_name, member in zip(self.component_names, self.components)]
        else:
            member_strs = [member._get_printable_str(shorten=True) for member in self.components] 

        return mod_str + f"{name_str}<{self.classification}({', '.join(member_strs)})>" 

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
        return self._get_printable_str()

    def has_member_attribute_with_name(self, name: str) -> bool:
        return name in self.component_names

    def get_member_attribute_by_name(self, name: str) -> TypeClass:
        if self.classification != TypeClass.classifications.struct and self.classification != TypeClass.classifications.interface:
            raise Exception(f"Can only get_member_attribute_by_name on struct constructions, got {self}")

        if name not in self.component_names:
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
            inherits=[])

    @classmethod
    def produce_tuple_type(cls, components: list[TypeClass], global_mod: Context) -> TypeClass:
        return TypeClass(
            classification=TypeClass.classifications.tuple, 
            name="",
            mod=global_mod, 
            components=components, 
            component_names=[], 
            inherits=[])

    @classmethod
    def produce_function_type(cls, arg: TypeClass, ret: TypeClass, mod: Context, name: str = "") -> TypeClass:
        return TypeClass(
            classification=TypeClass.classifications.function, 
            name=name, 
            mod=mod, 
            components=[arg, ret], 
            component_names=["arg", "ret"], 
            inherits=[])

    @classmethod
    def produce_proto_struct_type(cls, name: str, mod: Context) -> TypeClass:
        return TypeClass(
            classification=TypeClass.classifications.proto_struct,
            name=name, 
            mod=mod, 
            components=[], 
            component_names=[], 
            inherits=[])

    @classmethod
    def produce_proto_interface_type(cls, name: str, mod: Context) -> TypeClass:
        return TypeClass(
            classification=TypeClass.classifications.proto_interface, 
            name=name, 
            mod=mod, 
            components=[], 
            component_names=[], 
            inherits=[])
