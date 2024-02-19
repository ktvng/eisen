from __future__ import annotations

from alpaca.concepts import Module, Type
from eisen.common.eiseninstance import Instance

class NodeData():
    def __init__(self):
        self.instances: list[Instance] = None
        self.returned_type: Type = None
        self.enters_module: Module = None
