from __future__ import annotations

from alpaca.concepts import Module
from eisen.common.eiseninstance import Instance

class NodeData():
    def __init__(self):
        self.instances: list[Instance] = None
        self.returned_type = None
        self.enters_module: Module = None
