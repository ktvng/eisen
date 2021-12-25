from __future__ import annotations
from alpaca.compiler._scope import Scope

class Context():
    def __init__(self, module, builder, scope : Scope):
        self.module = module
        self.builder = builder
        self.scope = scope
