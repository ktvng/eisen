from __future__ import annotations

import alpaca
from alpaca.lexer import Token
from alpaca.clr import CLRList

from seer.parsing.builder import SeerBuilder

class CustomParser2:
    def __init__(self, config: alpaca.config.Config):
        self.config = config
        self.cfg = config.cfg
        self.builder = SeerBuilder()

        # create the algo to parse the action CFG        
        self.action_cfg = self.cfg.get_subgrammar_from("ACTION")
        normer = alpaca.grammar.CFGNormalizer()
        cfg = normer.run(self.action_cfg)
        self.action_algo = alpaca.parser.cyk.CYKAlgo(cfg)


    def parse(self, toks: list[Token]):
        return self.parse_action(toks)

    def parse_action(self, toks: list[Token]):
        self.action_algo.parse(toks)
        astbuilder = alpaca.parser.cyk.AstBuilder()
        asl = astbuilder.run(self.config, self.action_algo.tokens, self.action_algo.dp_table, 
            self.builder, starting_rule="ACTION")
        return asl