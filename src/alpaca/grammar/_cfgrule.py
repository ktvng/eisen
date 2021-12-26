from __future__ import annotations
from alpaca.grammar._action import Action

class CFGRule():
    def __init__(self, production_symbol : str, pattern_str : str, action : Action):
        self.production_symbol = production_symbol
        self.pattern_str = pattern_str
        self.pattern = [s.strip() for s in pattern_str.split(' ') if s != ""]

        if isinstance(action, list):
            self.actions = action
        else:
            self.actions = [action]

    def __str__(self):
        return f"{self.production_symbol} -> {self.pattern_str}"
