from __future__ import annotations

from grammar import CFGRule
from config._regextokenrule import RegexTokenRule

class Config():
    class CFG():
        def __init__(self, rules : list[CFGRule]):
            self.rules = rules

    def __init__(self, regex_rules : list[RegexTokenRule], cfg_rules : list[CFGRule]):
        self.regex_rules = regex_rules
        self.cfg_rules = cfg_rules
        self.cfg = Config.CFG(cfg_rules)
