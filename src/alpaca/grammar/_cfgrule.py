from __future__ import annotations
from alpaca.grammar._action import Action

"""
A rule inside a Context Free Grammar (CFG). Should be parsed from some grammar
configuration file.
"""
class CFGRule():
    def __init__(self,
            production_symbol: str,
            pattern_str: str,
            action: Action,
            original_entry: str = None):

        self.production_symbol = production_symbol
        self.pattern_str = pattern_str
        self.pattern = [s.strip() for s in pattern_str.split(' ') if s != ""]
        self.original_entry = original_entry

        if isinstance(action, list):
            self.actions = action
        else:
            self.actions = [action]

    def __str__(self):
        return f"{self.production_symbol} -> {self.pattern_str}"

    def __eq__(self, __o: object) -> bool:
        return hash(self) == hash(__o)

    def __hash__(self) -> int:
        return hash(self.production_symbol + self.pattern_str)

    def copy(self) -> CFGRule:
        return CFGRule(self.production_symbol, self.pattern_str, self.actions, self.original_entry)
