from __future__ import annotations
from grammar._cfgrule import CFGRule

class CFG():
    def __init__(self, rules : list[CFGRule]):
        self.rules = rules

