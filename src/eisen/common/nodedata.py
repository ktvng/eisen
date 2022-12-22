from __future__ import annotations

from alpaca.concepts import TypeClass
from eisen.common import EisenInstance, Module

class NodeData():
    def __init__(self):
        self.instances: list[EisenInstance] = None
        self.returned_typeclass = None
        self.enters_module: Module = None