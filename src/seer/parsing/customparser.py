from __future__ import annotations

import alpaca
from alpaca.lexer import Token
from alpaca.clr import CLRList

class PartialStructure:
    def __init__(self, expected: list[str], toks: list[Token]):
        self.expected = expected
        self.toks = toks

    def is_expected(self, state: str) -> bool:
        return state in self.expected

class CustomParser:
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

    @classmethod
    def split(cls, toks: list[Token]) -> list[PartialStructure]:
        headers_and_expected = [
            ("fn", "CONTEXT"), 
            ("create", "STRUCT_CONSTRUCTOR"),
            ("struct", "CONTEXT"),
            ("interface", "CONTEXT"),
            ("mod", "CONTEXT"), 
            ("if", "IF_CONTEXT"),
            ("while", "WHILE_CONTEXT")
        ]

        chunks = []
        remainder = toks
        while remainder:
            found_header = False
            for header, expected in headers_and_expected:
                if remainder[0].type == header:
                    found_header = True
                    header_list, remainder = cls._split_header_block(header, remainder)
                    chunks.append(PartialStructure(expected=[expected], toks=header_list))
                    break
            
            if not found_header:
                raise Exception(f"error? no header matches '{remainder[0].type}'")

        return chunks

    @classmethod
    def run(cls, config: alpaca.config.Config, toks: list[Token], builder):
        normer = alpaca.grammar.CFGNormalizer()
        cfg = normer.run(config.cfg)
        algo = alpaca.parser.cyk.CYKAlgo(cfg)
        chunks = cls.split(toks)
        asls = []
        for chunk in chunks:
            algo.parse(chunk.toks)
            astbuilder = alpaca.parser.cyk.AstBuilder()
            asl = astbuilder.run(config, algo.tokens, algo.dp_table, builder, starting_rule=chunk.expected[0])
            asls.append(asl)

        algo.parse_clrtokens(asls)
        astbuilder = alpaca.parser.cyk.AstBuilder()
        return CLRList("start", lst=asls)
            
    
            
            

        
        


