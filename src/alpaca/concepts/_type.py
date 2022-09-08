from __future__ import annotations
from typing import Literal, Any

_novel = "novel"
_tuple = "tuple"
_struct = "struct"
_function = "function"
_maybe = "maybe"
TypeConstruction = Literal["novel", "tuple", "struct", "function", "maybe"]

class Type():
    def __init__(self, 
            name: str, 
            construction: TypeConstruction,
            components: list[Type] = [],
            component_names: list[str] = []):

        self.name = name
        self.construction = construction
        self.components = components
        self.component_names = component_names

        if component_names and len(component_names) != len(components):
            raise Exception("Types must have the same number of components as component names.")

    def _equiv(self, u : list, v : list) -> bool:
        return (u is not None 
            and v is not None 
            and len(u) == len(v) 
            and all([x == y for x, y in zip(u, v)]))

    def __eq__(self, o: Any) -> bool:
        # TODO: can we return hash == hash here?
        if not isinstance(o, Type):
            return False
        if self.construction == _novel and o.construction == _novel:
            return self.name == o.name
        return (self._equiv(self.components, o.components)
            and self._equiv(self.component_names, o.component_names))

    def _get_unique_string_id(self) -> str:
        if self.construction == _novel:
            return self.name

        if self.component_names:
            member_strs = [f"{member_name}:{member._get_unique_string_id()}" 
                for member_name, member in zip(self.component_names, self.components)]
        else:
            member_strs = [member._get_unique_string_id() for member in self.components] 

        return f"{self.construction}({', '.join(member_strs)})"

    def __hash__(self) -> int:
        return hash(self._get_unique_string_id())
        
    def __str__(self) -> str:
        return f"<{self.name}({self._get_unique_string_id()})>"

    def get_member_attribute_by_name(self, name: str) -> Type:
        if self.construction != _struct:
            raise Exception(f"Can only get_member_attribute_by_name on struct constructions, got {self}")

        if name not in self.component_names:
            raise Exception(f"Type {self} does not have member attribute named '{name}'")

        pos = self.component_names.index(name)
        return self.components[pos]

    def get_return_type(self) -> Type:
        if self.construction != _function:
            raise Exception(f"Can only get_return_type on function constructions, got {self}")
        
        return self.components[1]

    def is_function(self) -> bool:
        return self.construction == _function

    def is_struct(self) -> bool:
        return self.construction == _struct

    def is_novel(self) -> bool:
        return self.construction == _novel

class TypeFactory:
    @classmethod
    def produce_novel_type(cls, name: str) -> Type:
        return Type(name, _novel)

    @classmethod
    def produce_tuple_type(cls, components: list[Type], name: str = "") -> Type:
        return Type(name, _tuple, components)

    @classmethod
    def produce_struct_type(cls, name: str, components: list[Type], component_names: list[str]) -> Type:
        return Type(name, _struct, components, component_names)

    # a function is represented as a "function" classification with argument and return 
    # values being the two components, respectively
    @classmethod
    def produce_function_type(cls, arg: Type, ret: Type, name: str = ""):
        return Type(name, _function, [arg, ret], ["arg", "ret"])

    @classmethod
    def produce_maybe_type(cls, components: list[Type], name: str = ""):
        return Type(name, _maybe, components)