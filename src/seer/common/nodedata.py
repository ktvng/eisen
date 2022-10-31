from __future__ import annotations

from alpaca.concepts import TypeClass
from seer.common import SeerInstance, Module

class NodeData():
    def __init__(self):
        self.instances: list[SeerInstance] = None
        self.returned_typeclass = None
        self.enters_module: Module = None