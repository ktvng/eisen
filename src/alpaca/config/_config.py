from __future__ import annotations

from alpaca.grammar import CFG, CFGRule
from alpaca.config._regextokenrule import RegexTokenRule

class Config():
    def __init__(self, 
            regex_rules : list[RegexTokenRule], 
            cfg_rules : list[CFGRule], 
            hierarchy : Config.TypeHierarchy):

        self.regex_rules = regex_rules
        self.cfg_rules = cfg_rules
        terminals = list(set(map(lambda x: x.type, regex_rules)))
        self.cfg = CFG(cfg_rules, terminals)
        self.type_hierachy = hierarchy

    class TypeHierarchy:
        def __init__(self):
            self.data = {}

        def is_child_type(self, child_type : str, parent_type : str) -> bool:
            return parent_type in self.data[child_type]

        def add_parent_types(self, child_type : str, parent_types : list[str] = []):
            if not child_type in self.data:
                self.data[child_type] = []

            self.data[child_type] += parent_types

        def parent_types_for(self, child_type : str) -> list[str]:
            return self.data.get(child_type, [])
