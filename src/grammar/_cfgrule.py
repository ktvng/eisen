from __future__ import annotations
from grammar._action import Action

class CFGRule():
    def __init__(self, production_symbol : str, pattern_str : str, action : Action):
        self.production_symbol = production_symbol
        self.pattern_str = pattern_str
        self.pattern = [s.strip() for s in pattern_str.split(' ') if s != ""]

        if isinstance(action, list):
            self.actions = action
            self.reverse_with = action
        else:
            
            self.actions = [action]
            # TODO: replace with above; here for back-compat
            self.reverse_with = [action]

    def __str__(self):
        return f"{self.production_symbol} -> {self.pattern_str}"

    @classmethod
    def is_production_symbol(cls, token : str):
        return token.isupper() and all(map(lambda x : x.isalnum() or x == '_', token))
