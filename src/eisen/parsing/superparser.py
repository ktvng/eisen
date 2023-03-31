from __future__ import annotations

import alpaca
from alpaca.lexer import Token
from alpaca.clr import CLRList, CLRToken

from eisen.parsing.builder import EisenBuilder


class ContextParser():
    def __init__(self, config: alpaca.config.Config, context_name: str):
        self.config = config

        normer = alpaca.grammar.CFGNormalizer()
        self.context_name = context_name
        self.cfg = normer.run(config.cfg.get_subgrammar_from(context_name))
        self.algo = alpaca.parser.cyk.CYKAlgo(self.cfg)
        self.builder = alpaca.parser.cyk.AstBuilder()
        self.extended_builder = EisenBuilder()

    def parse(self, tokens: list[Token]):
        self.algo.parse(tokens)
        ast = self.builder.run(
            self.config,
            self.algo.tokens,
            self.algo.dp_table,
            self.extended_builder,
            self.context_name)
        return ast

class ParserSelector:
    context_type_to_parser_map = {
        "variant": "VARIANT",
        "interface": "INTERFACE",
        "struct": "STRUCT",
        "fn": "FUNC",
        "mod": "MOD",
    }

    @classmethod
    def _get_parser(cls, context_name: str, parsers: list[ContextParser]) -> ContextParser:
        return next(parser for parser in parsers if parser.context_name == context_name)

    @classmethod
    def select_parser(cls, context_tokens: list[Token], parsers: list[ContextParser]) -> ContextParser:
        first_token_type = context_tokens[0].type
        return cls._get_parser(cls.context_type_to_parser_map[first_token_type], parsers)

class ModParser(ContextParser):
    def __init__(self, parsers: list[ContextParser]):
        self.parsers = parsers + [self]
        self.context_name = "MOD"

    def parse(self, tokens: list[Token]):
        line_number = tokens[0].line_number
        contexts = [CLRToken(type_chain=["TAG"],
                             value=tokens[1].value,
                             line_number=tokens[1].line_number)]

        # remove the outer mod
        remaining_tokens = tokens[3:-1]
        while remaining_tokens:
            context_tokens, remaining_tokens = self.get_context_tokens(remaining_tokens)
            parser = ParserSelector.select_parser(context_tokens, self.parsers)
            asl = parser.parse(context_tokens)
            contexts.append(asl)

        return self.create_mod_asl(line_number, contexts)

    def get_context_tokens(self, tokens: list[Token]) -> tuple[list[Token], list[Token]]:
        return ContextSeparator.split_context(tokens)

    def create_mod_asl(self, line_number: int, contexts: list[CLRList]):
        return alpaca.clr.CLRList(
            type="mod",
            lst=contexts,
            line_number=line_number)

class SuperParser():
    def __init__(self, config: alpaca.config.Config):
        self.func_parser = ContextParser(config, "FUNC")
        self.struct_parser = ContextParser(config, "STRUCT")
        self.interface_parser = ContextParser(config, "INTERFACE")
        self.variant_parser = ContextParser(config, "VARIANT")
        self.mod_parser = ModParser([
            self.func_parser,
            self.struct_parser,
            self.interface_parser,
            self.variant_parser
        ])

        self.parsers = [
            self.func_parser,
            self.struct_parser,
            self.interface_parser,
            self.variant_parser,
            self.mod_parser,
        ]

    def parse(self, tokens: list[Token]) -> CLRList:
        remaining_tokens = tokens
        contexts = []
        while remaining_tokens:
            context_tokens, remaining_tokens = ContextSeparator.split_context(remaining_tokens)
            parser = ParserSelector.select_parser(context_tokens, self.parsers)
            asl = parser.parse(context_tokens)
            contexts.append(asl)

        return alpaca.clr.CLRList(
            type="start",
            lst=contexts,
            line_number=tokens[0].line_number)

class ContextSeparator():
    @classmethod
    def split_context(cls, toks: list[Token]) -> tuple[list[Token], list[Token]]:
        header_list = []

        pos = 0
        len_ends = 0
        while toks[pos].type == "endl":
            len_ends += 1
            pos += 1

        while toks[pos].type != "{" and pos < len(toks):
            header_list.append(toks[pos])
            pos += 1

        if pos == len(toks):
            raise Exception(f"syntax error: expected to find open curly brace after header")

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
            raise Exception(f"syntax error: expected to find closing curly brace for header but did not")

        # here we have a populated struct list including the final "}" token, we
        # return the header_list and the remainng tokens
        return header_list, toks[len(header_list) + len_ends: ]
