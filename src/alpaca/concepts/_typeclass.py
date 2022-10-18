from __future__ import annotations
from typing import Any

import uuid

from alpaca.concepts._type import Type
from alpaca.concepts._context import Context

class TypeClass2():
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

        if self.classification == TypeClass2.classifications.proto_interface:
            self.classification = TypeClass2.classifications.interface
        elif self.classification == TypeClass2.classifications.proto_struct:
            self.classification = TypeClass2.classifications.struct

        self.components = components 
        self.component_names = component_names
        self.inherits = inherits

    def _get_uuid_str(self) -> str:
        mod_str = self.mod.get_full_name() if self.mod else ""
        if self.classification == TypeClass2.classifications.novel:
            return mod_str + "::" + self.name

        name_str = self.name if self.name else ""

        if self.component_names:
            member_strs = [f"{member_name}:{member._get_uuid_str()}" 
                for member_name, member in zip(self.component_names, self.components)]
        else:
            member_strs = [member._get_uuid_str() for member in self.components] 

        return mod_str + "::" + f"{name_str}={self.classification}({', '.join(member_strs)})" 

    def _get_printable_str(self, shorten: bool = False) -> str:
        mod_str = self.mod.get_full_name() if self.mod else ""
        if self.classification == TypeClass2.classifications.novel:
            return mod_str + "::" + self.name

        if shorten and self.name:
            return self.name

        name_str = self.name + "=" if self.name else ""

        if self.component_names:
            member_strs = [f"{member_name}<{member._get_printable_str(shorten=True)}" 
                for member_name, member in zip(self.component_names, self.components)]
        else:
            member_strs = [member._get_printable_str(shorten=True) for member in self.components] 

        return mod_str + "::" + f"{name_str}{self.classification}({', '.join(member_strs)})" 

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

    def get_member_attribute_by_name(self, name: str) -> Type:
        if self.classification != TypeClass2.classifications.struct and self.classification != TypeClass2.classifications.interface:
            raise Exception(f"Can only get_member_attribute_by_name on struct constructions, got {self}")

        if name not in self.component_names:
            raise Exception(f"Type {self} does not have member attribute named '{name}'")

        pos = self.component_names.index(name)
        return self.components[pos]

    def get_return_type(self) -> Type:
        if self.classification != TypeClass2.classifications.function:
            raise Exception(f"Can only get_return_type on function constructions, got {self}")
        
        return self.components[1]

    def is_function(self) -> bool:
        return self.classification == TypeClass2.classifications.function

    def is_struct(self) -> bool:
        return self.classification == TypeClass2.classifications.struct

    def is_novel(self) -> bool:
        return self.classification == TypeClass2.classifications.novel 


class TypeClassFactory():
    @classmethod
    def produce_novel_type(cls, name: str, global_mod: Context) -> TypeClass2:
        return TypeClass2(
            classification=TypeClass2.classifications.novel, 
            name=name, 
            mod=global_mod, 
            components=[], 
            component_names=[], 
            inherits=[])

    @classmethod
    def produce_tuple_type(cls, components: list[TypeClass], global_mod: Context) -> TypeClass2:
        return TypeClass2(
            classification=TypeClass2.classifications.tuple, 
            name="",
            mod=global_mod, 
            components=components, 
            component_names=[], 
            inherits=[])

    @classmethod
    def produce_function_type(cls, arg: TypeClass, ret: TypeClass, mod: Context, name: str = "") -> TypeClass2:
        return TypeClass2(
            classification=TypeClass2.classifications.function, 
            name=name, 
            mod=mod, 
            components=[arg, ret], 
            component_names=["arg", "ret"], 
            inherits=[])

    @classmethod
    def produce_proto_struct_type(cls, name: str, mod: Context) -> TypeClass2:
        return TypeClass2(
            classification=TypeClass2.classifications.proto_struct,
            name=name, 
            mod=mod, 
            components=[], 
            component_names=[], 
            inherits=[])

    @classmethod
    def produce_proto_interface_type(cls, name: str, mod: Context) -> TypeClass2:
        return TypeClass2(
            classification=TypeClass2.classifications.proto_interface, 
            name=name, 
            mod=mod, 
            components=[], 
            component_names=[], 
            inherits=[])

class TypeClass():
    class classifications:
        novel = "novel"
        tuple = "tuple"
        function = "function"
        struct = "struct"
        interface = "interface"
        proto_struct = "proto_struct"
        proto_interface = "proto_interface"

    def __init__(self, 
            classification: str, 
            name: str, 
            type: Type, 
            context: Context, 
            inherits: list[TypeClass] = []) -> None:

        self.name = name
        self.classification = classification
        self.type = type 
        self.context = context
        self.inherits = inherits

        self.guid = uuid.uuid4()

    @classmethod
    def create_general(cls, type: Type) -> TypeClass:
        return TypeClass(TypeClass.classifications.general, None, type, None, None)

    @classmethod
    def create_proto_struct(cls, name: str, mod: Context) -> TypeClass:
        return TypeClass(TypeClass.classifications.proto_struct, name, None, mod, None)

    @classmethod
    def create_proto_interface(cls, name: str, mod: Context) -> TypeClass:
        return TypeClass(TypeClass.classifications.proto_interface, name, None, mod, None)

    @classmethod
    def create_struct(cls, name: str, type: Type, context: Context, inherits: list[TypeClass] = []) -> TypeClass:
        return TypeClass(TypeClass.classifications.struct, name, type, context, inherits)

    @classmethod
    def create_interface(cls, name: str, type: Type, context: Context) -> TypeClass:
        return TypeClass(TypeClass.classifications.interface, name, type, context)

    def finalize(self, type: Type, inherits: list[TypeClass] = []):
        if (self.classification != TypeClass.classifications.proto_interface and
            self.classification != TypeClass.classifications.proto_struct):
            raise Exception("can only finalize a proto* TypeClass")

        self.type = type
        self.inherits = inherits

    def __hash__(self) -> int:
        return self.guid.int

    def __str__(self) -> str:
        s = str(self.type)
        if self.inherits:
            s += ":: " + ", ".join(s.name for s in self.inherits)
        if self.context:
            s += " in " + self.context.name

        return s
