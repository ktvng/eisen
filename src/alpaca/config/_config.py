from __future__ import annotations

from alpaca.grammar import CFG, CFGRule
from alpaca.config._regextokenrule import RegexTokenRule

class Config():
    def __init__(self, regex_rules : list[RegexTokenRule], cfg_rules : list[CFGRule]):
        self.regex_rules = regex_rules
        self.cfg_rules = cfg_rules
        terminals = list(map(lambda x: x.get_identifier(), regex_rules))
        self.cfg = CFG(cfg_rules, terminals)
