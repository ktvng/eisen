from __future__ import annotations
from alpaca.grammar._cfgrule import CFGRule

from functools import reduce

class CFG():
    def __init__(self, rules : list[CFGRule], terminals : list[str]):
        self.rules = rules
        self.terminals = terminals
        self._rules_map: dict[str, list[CFGRule]] = {}
        self._init_rules_map()

    def _init_rules_map(self):
        for rule in self.rules:
            symbol = rule.production_symbol
            if symbol in self._rules_map:
                continue

            all_rules_with_symbol = self._get_rules_for_production_symbol(symbol)
            self._rules_map[symbol] = all_rules_with_symbol

    def get_all_rules_for_production_symbol(self, symbol: str) -> list[CFGRule]:
        return self._rules_map.get(symbol, [])

    def is_production_symbol(self, rule_symbol : str):
        return rule_symbol not in self.terminals

    def __str__(self):
        return reduce(lambda s, rule: s + str(rule) + "\n", self.rules, "")

    def _get_rules_for_production_symbol(self, symbol: str) -> list[CFGRule]:
        return [rule for rule in self.rules if rule.production_symbol == symbol]

    def get_subgrammar_from(self, symbol: str):
        sub_grammar_rules = []
        processing_queue = self.get_all_rules_for_production_symbol(symbol)
        while processing_queue:
            rule = processing_queue.pop(0)
            sub_grammar_rules.append(rule)
            for child_symbol in rule.pattern:
                if self.is_production_symbol(child_symbol):
                    rules_of_child_symbol = self.get_all_rules_for_production_symbol(child_symbol)
                    for child_rule in rules_of_child_symbol:
                        if child_rule not in processing_queue and child_rule not in sub_grammar_rules:
                            processing_queue.append(child_rule)

        return CFG(sub_grammar_rules, self.terminals)
