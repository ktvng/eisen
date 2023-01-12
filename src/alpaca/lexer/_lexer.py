from __future__ import annotations
import re

from functools import reduce

from alpaca.config import Config

from alpaca.lexer._token import Token
from alpaca.lexer._abstractcallback import AbstractCallback

def run(text : str, config : Config, callback : AbstractCallback) -> list[Token]:
    return Lexer.run(text, config, callback)

class Lexer():
    _newline_regex = re.compile("\n+")

    @classmethod
    def run(cls, text : str, config : Config, callback : AbstractCallback):
        tokens = []
        line_number = 1
        while text:
            match_tuples = [rule.match(text) for rule in config.regex_rules]
            longest_match = reduce(
                lambda a, b: a if a[1] >= b[1] else b,
                match_tuples)

            token_value, match_len, rule = longest_match
            line_number += token_value.count('\n')

            text = text[match_len :]
            if match_len == 0:
                raise Exception(f"Error: no regex matches, head of input: {text[0:10]}")

            if rule.type == "none":
                continue

            # apply a processing function based on the rule.type
            if callback is not None:
                matching_types = rule.type_chain
                for type in matching_types:
                    if hasattr(callback, type):
                        f = getattr(callback, type)
                        token_value = f(token_value)

            new_token = Token(rule.type, token_value, line_number, rule)
            tokens.append(new_token)

        return tokens
