from __future__ import annotations
from alpaca.concepts._nested_container import NestedContainer

class Module(NestedContainer):
    def _add_child(self, child: NestedContainer):
        if isinstance(child, Module):
            self.children.append(child)
            