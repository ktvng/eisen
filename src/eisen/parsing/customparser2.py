from __future__ import annotations
from abc import ABC, abstractmethod

import alpaca
from alpaca.lexer import Token
from alpaca.clr import CLRList

from eisen.parsing.builder import EisenBuilder


class PartialListOfTokens(ABC):
    @abstractmethod
    def process(self) -> tuple[list[CLRList], list[LooseTokens | Chunk | Unprocessed]]:
        pass



class LooseTokens(PartialListOfTokens):
    def __init__(self, toks: list[Token]):
        self.tokens = toks

class Chunk(PartialListOfTokens):
    def __init__(self, toks: list[Token]):
        self.tokens = toks
    
class Unprocessed(PartialListOfTokens):
    def __init__(self, toks: list[Token]):
        self.tokens = toks


class CustomParser2:
    def __init__(self, config: alpaca.config.Config):
        self.config = config
        self.cfg = config.cfg
        self.builder = EisenBuilder()

        # create the algo to parse the action CFG        
        self.action_cfg = self.cfg.get_subgrammar_from("ACTION")
        normer = alpaca.grammar.CFGNormalizer()
        cfg = normer.run(self.action_cfg)
        self.action_algo = alpaca.parser.cyk.CYKAlgo(cfg)

    headers = ["fn", "create", "struct", "interface" "mod", "if", "while"]

    # Split out thing blocks with headers. These will look something like this:
    #
    #   header some content {
    #       stuff inside
    #       the header block
    #   }
    #
    @classmethod
    def _split_header_block(cls, header: str, toks: list[Token]) -> tuple[list[Token], list[Token]]:
        header_list = []
        if toks[0].type != header:
            raise Exception(f"expected {header} but got '{toks[0].type}'")

        pos = 0
        while toks[pos].type != "{" and pos < len(toks):
            header_list.append(toks[pos])
            pos += 1

        if pos == len(toks):
            raise Exception(f"syntax error: expected to find open curly brace after header {header} ")

        # currently at the first "{" token, but it was not added to the header_list
        # yet
        header_list.append(toks[pos])

        # we are now after the first "{" token, and inside the block
        pos += 1
        block_level = 1

        # add all tokens to the header_list until the final "}" is encountered
        while block_level != 0 and pos < len(toks):
            header_list.append(toks[pos])
            if toks[pos].type == "{":
                block_level += 1
            elif toks[pos].type == "}":
                block_level -= 1
            pos += 1

        if pos == len(toks) and block_level != 0:
            raise Exception(f"syntax error: expected to find closing curly brace for {header} but did not")

        # here we have a populated struct list including the final "}" token, we
        # return the header_list and the remainng tokens
        return header_list, toks[len(header_list): ]


    def _parse_internal(self, parts: list[LooseTokens | Chunk | Unprocessed]):
        clr = []
        while parts:
            part = parts.pop(0)
            clrtokens, other_parts = part.process()
            parts.extend(other_parts)

    def _parse_remainder(self, toks: list[Token]) -> list[CLRList]:
        clrlists = []
        while toks:
            if toks[0].type in CustomParser2.headers:
                header_toks, remainder = self._split_header_block(toks[0].type, toks)
                asls = self._parse_header(toks[0].type, header_toks)
            else:
                asls, remainder = self._parse_action(toks)
            clrlists.extend(asls)
            toks = remainder
        return clrlists

    def _parse_header(self, header_type: str, header_toks: list[Token]):
        if header_type == "mod":
            self._parse_mod(header_toks)

    def _parse_mod(self, header_toks: list[Token]):
        clritems = [header_toks[1]]
        

        
            





    def parse(self, toks: list[Token]):
        return self._parse_action(toks)

    def _parse_action(self, toks: list[Token]):
        self.action_algo.parse(toks)
        astbuilder = alpaca.parser.cyk.AstBuilder()
        asl = astbuilder.run(self.config, self.action_algo.tokens, self.action_algo.dp_table, 
            self.builder, starting_rule="ACTION")
        return asl