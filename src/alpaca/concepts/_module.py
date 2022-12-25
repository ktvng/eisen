from __future__ import annotations
from alpaca.concepts._nested_container import NestedContainer

class Module(NestedContainer):
    """a module is a hierarchical container which holds functions, 
    struct/interface definitions, and other modules"""
    def _add_child(self, child: NestedContainer):
        if isinstance(child, Module):
            self.children.append(child)
