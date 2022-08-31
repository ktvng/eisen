from alpaca.grammar import CFGNormalizer
from alpaca.asts import AST
from alpaca.parser.cyk import CYKParser
from alpaca.config import Config
from alpaca.parser._builder import Builder

from error import Raise

def run(config: Config, tokens: list, builder: Builder, algo: str="cyk") -> AST:
    if not tokens:
        raise Exception("No tokens passed into run.")

    if algo == "cyk":
        return CYKParser(config, tokens, builder)
    else:
        raise Exception("Error: unknown parser algo")
