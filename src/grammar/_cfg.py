from __future__ import annotations
from grammar._cfgrule import CFGRule

class CFG():
    def __init__(self, rules : list[CFGRule], terminals : list[str]):
        self.rules = rules
        self.terminals = terminals

    def is_production_symbol(self, rule_symbol : str):
        return rule_symbol not in self.terminals
