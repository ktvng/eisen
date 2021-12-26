from alpaca.grammar import CFGNormalizer
from alpaca.asts import AST
from alpaca.parser.cyk import CYKParser
from alpaca.parser._abstractbuilder import AbstractBuilder
from alpaca.config import Config

from error import Raise

def run(config : Config, tokens : list, builder : AbstractBuilder, algo : str="cyk") -> AST:
    if not tokens:
        return None

    if algo == "cyk":
        return CYKParser(config, tokens, builder)
    else:
        Raise.code_error("Error: unknown parser algo")
