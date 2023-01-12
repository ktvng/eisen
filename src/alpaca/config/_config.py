from __future__ import annotations

from alpaca.grammar import CFG, CFGRule
from alpaca.config._tokenrule import TokenRule

class Config():
    def __init__(self, regex_rules: list[TokenRule], cfg_rules: list[CFGRule]):
        self.regex_rules = regex_rules
        self.cfg_rules = cfg_rules
        terminals = list(set(map(lambda x: x.type, regex_rules)))
        self.cfg = CFG(cfg_rules, terminals)
