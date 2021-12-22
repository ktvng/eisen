from __future__ import annotations
import re

from functools import reduce
import typing

from config import Config
from error import Raise

from lexer._token import Token

class Lexer():
    _newline_regex = re.compile("\n+")

    @classmethod
    def run(cls, text : str, config : Config, callback : typing.Any=None):
        tokens = []
        line_number = 1
        while text:
            match_tuples = [rule.match(text) for rule in config.regex_rules]
            longest_match = reduce(
                lambda a, b: a if a[1] >= b[1] else b, 
                match_tuples)

            match_str, match_len, rule = longest_match
            token_value = rule.value if rule.value is not None else match_str
            line_number += match_str.count('\n')
            if rule.type != "none":
                # apply a processing function based on the rule.type
                if callback is not None and hasattr(callback, rule.type):
                    f = getattr(callback, rule.type)

                    if f is not None:
                        try:
                            token_value = f(token_value)
                        except:
                            Raise.code_error(f"Supplied callback has no callable function for {rule.type}")

                new_token = Token(rule.type, token_value, line_number)
                tokens.append(new_token)

            text = text[match_len :]
            if match_len == 0:
                Raise.code_error(f"Error: no regex matches, head of input: {text[0:10]}")

        return tokens
