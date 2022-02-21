from __future__ import annotations
from alpaca.grammar._cfgrule import CFGRule

from functools import reduce

class CFG():
    def __init__(self, rules : list[CFGRule], terminals : list[str]):
        self.rules = rules
        self.terminals = terminals

    def is_production_symbol(self, rule_symbol : str):
        return rule_symbol not in self.terminals

    def __str__(self):
        return reduce(lambda s, rule: s + str(rule) + "\n", self.rules, "")