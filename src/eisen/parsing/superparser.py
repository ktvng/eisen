from __future__ import annotations
from abc import ABC, abstractmethod

import alpaca
from alpaca.lexer import Token
from alpaca.clr import AST, ASTToken

from eisen.parsing.builder import EisenBuilder

def convert_to_ASTToken(token: Token) -> ASTToken:
    """
    Convert a lexer [token] to an ASTToken
    """
    return ASTToken(type_chain=["TAG"], value=token.value, line_number=token.line_number)


class ParserSelector:
    """
    Logic to select the correct parser for a some list of tokens.
    """

    # Maps the token type of the lexer token to the [context_name] of a parser.
    token_type_to_parser_map = {
        "interface": "INTERFACE",
        "struct": "STRUCT",
        "fn": "FUNC",
        "mod": "MOD",
        "trait": "TRAIT",
        "impl": "TRAIT_DEF"
    }

    @staticmethod
    def select_parser(tokens: list[Token], parsers: list[ComponentParser]) -> ComponentParser:
        """
        Choose the right parser out of the provided [parsers] that can parse the given [tokens]
        """
        name_of_context_to_be_parsed = ParserSelector.token_type_to_parser_map[tokens[0].type]
        return next(parser for parser in parsers
                    if parser.get_context_name() == name_of_context_to_be_parsed)

    @staticmethod
    def parse_remaining(remaining_tokens: list[Token], parsers: list[ComponentParser]) -> list[AST]:
        """
        Select the right parser from the list of [parsers] to parse the [remaining_tokens] into
        a list of ASTs sequentially. Keeps selecting and using parsers until all [remaining_tokens]
        are accounted for.
        """
        parsed_asts = []
        while remaining_tokens:
            context_tokens, remaining_tokens = ContextSeparator.split_context(remaining_tokens)
            if not context_tokens and not remaining_tokens: break

            parser_to_use = ParserSelector.select_parser(context_tokens, parsers)
            ast = parser_to_use.parse(context_tokens)
            parsed_asts.append(ast)
        return parsed_asts

class ComponentParser(ABC):
    @abstractmethod
    def parse(self, tokens: list[Token]) -> AST:
        """
        Parse a list of [tokens] into an AST (Abstract Syntax Tree)
        """
        ...

    def get_context_name(self) -> str:
        """
        The context name corresponds to the production rule in the grammar.gm which this parser
        is capable of parsing.
        """
        return self.context_name

class ContextParser(ComponentParser):
    def __init__(self, config: alpaca.config.Config, context_name: str):
        self.config = config
        normer = alpaca.grammar.CFGNormalizer()
        self.context_name = context_name
        self.cfg = normer.run(config.cfg.get_subgrammar_from(context_name))
        self.algo = alpaca.parser.cyk.CYKAlgo(self.cfg)
        self.builder = alpaca.parser.cyk.AstBuilder()
        self.extended_builder = EisenBuilder()

    def parse(self, tokens: list[Token]) -> AST:
        self.algo.parse(tokens)
        return self.builder.run(
            config=self.config,
            nodes=self.algo.tokens,
            dp_table=self.algo.dp_table,
            builder=self.extended_builder,
            starting_rule=self.context_name)

class ModParser(ComponentParser):
    def __init__(self, parsers: list[ContextParser]):
        # As modules can exist inside other modules, add 'self' to the list of parsers
        self.parsers = parsers + [self]
        self.context_name = "MOD"

    def parse(self, tokens: list[Token]):
        """
        The known and fixed syntax for a module declaration:

        0   2        3
        mod MOD_NAME {
            ...
            ...

        }
        n-1
        """
        line_number = tokens[0].line_number
        children = [convert_to_ASTToken(tokens[1])]

        # remove the outer mod, then parse the remaining
        remaining_tokens = tokens[3:-1]
        additional_children = ParserSelector.parse_remaining(remaining_tokens, self.parsers)
        return alpaca.clr.AST(
            type="mod",
            lst=children + additional_children,
            line_number=line_number)

class TraitDefParser(ComponentParser):
    def __init__(self, parsers: list[ContextParser]):
        self.parsers = parsers
        self.context_name = "TRAIT_DEF"

    def parse(self, tokens: list[Token]) -> AST:
        """
        The known and fixed syntax for a trait implementation:

        0    1          2   3                 4
        impl TRAIT_NAME for IMPLEMENTING_TYPE {
            ...
            ...
        }
        n-1
        """
        # first children are the TRAIT_NAME and IMPLEMENTING_TYPE
        children = [convert_to_ASTToken(tokens[1]), convert_to_ASTToken(tokens[3])]

        # remove the trait_def tokens, then parse the remaining
        remaining_tokens = tokens[5:-1]
        additional_children = ParserSelector.parse_remaining(remaining_tokens, self.parsers)

        # create the trait_def AST
        return alpaca.clr.AST(
            type="trait_def",
            lst=children + additional_children,
            line_number=tokens[0].line_number)


class SuperParser(ComponentParser):
    """
    Parses a well formed Eisen program into a complete AST.
    """

    def __init__(self, config: alpaca.config.Config):
        self.context_name = "START"
        self.func_parser = ContextParser(config, "FUNC")
        self.struct_parser = ContextParser(config, "STRUCT")
        self.interface_parser = ContextParser(config, "INTERFACE")
        self.trait_parser = ContextParser(config, "TRAIT")

        # currently only functions are supported inside a trait definition
        self.trait_def_parser = TraitDefParser(parsers=[
            self.func_parser
        ])

        self.mod_parser = ModParser(parsers=[
            self.func_parser,
            self.struct_parser,
            self.interface_parser,
            self.trait_def_parser,
        ])

        self.parsers = [
            self.func_parser,
            self.struct_parser,
            self.interface_parser,
            self.mod_parser,
            self.trait_parser,
            self.trait_def_parser
        ]

    def parse(self, tokens: list[Token]) -> AST:
        children = ParserSelector.parse_remaining(tokens, self.parsers)
        return alpaca.clr.AST(
            type="start",
            lst=children,
            line_number=tokens[0].line_number)

class ContextSeparator():
    @staticmethod
    def remove_comments_and_whitespaces(toks: list[Token]) -> tuple[int, int]:
        while toks[pos].type == "endl":
            len_ends += 1
            pos += 1

    @staticmethod
    def split_context(toks: list[Token]) -> tuple[list[Token], list[Token]]:
        header_list = []

        pos = 0
        len_ends = 0

        while pos < len(toks) and toks[pos].type == "endl":
            len_ends += 1
            pos += 1

        if pos >= len(toks):
            return [], []

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
        # return the header_list and the remaining tokens
        return header_list, toks[len(header_list) + len_ends: ]
