from __future__ import annotations
from error import Raise

class Scope():
    def __init__(self, parent_scope : Scope = None):
        self._parent_scope = parent_scope
        self._defined_types = {}
        self._defined_objects = {}

    def get_ir_type(self, type : str):
        found_type = self._defined_types.get(type, None)
        if found_type is None and self._parent_scope is not None:
            found_type = self._parent_scope.get_ir_type(type)
        
        if found_type is None:
            Raise.error(f"cannot find type: {type}")
        
        return found_type

    def get_object(self, name : str):
        found_obj = self._defined_objects.get(name, None)
        if found_obj is None and self._parent_scope is not None:
            found_obj = self._parent_scope.get_object(name)
        
        return found_obj

    def add_obj(self, name : str, compiler_obj):
        if self._defined_objects.get(name, None) is not None:
            Raise.error(f"name {name} is already defined in this scope")

        self._defined_objects[name] = compiler_obj
    
    def add_type(self, type : str, ir_type):
        if self._defined_types.get(type, None) is not None:
            Raise.error(f"type {type} is already defined")
        
        self._defined_types[type] = ir_type
        