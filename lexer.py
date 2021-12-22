from __future__ import annotations
import re

from functools import reduce
import typing

from config import Config
from error import Raise

class Token2():
    def __init__(self, type : str, value : str, line_number : int):
        self.type = type
        self.value = value
        self.line_number = line_number

    type_print_len = 16
    def __str__(self):
        padding = max(0, self.type_print_len - len(self.type))
        return f"{self.line_number}\t{self.type}{' ' * padding}{self.value}"

class Lexer():
    _newline_regex = re.compile("\n+")

    @classmethod
    def _try_increment_line_number(cls, text : str):
        match = cls._newline_regex.match(text)
        if match:
            return len(match.group(0))
        
        return 0

    @classmethod
    def run(cls, text : str, config : Config, callback : typing.Any=None):
        tokens = []
        line_number = 1
        while text:
            match_tuples = [rule.match(text) for rule in config.regex_rules]
            longest_match = reduce(
                lambda a, b: a if a[1] >= b[1] else b, 
                match_tuples)

            line_number += cls._try_increment_line_number(text)
            match_str, match_len, rule = longest_match
            token_value = rule.value if rule.value is not None else match_str
            if rule.type != "none":
                # apply a processing function based on the rule.type
                if callback is not None and hasattr(callback, rule.type):
                    f = getattr(callback, rule.type)

                    if f is not None:
                        try:
                            token_value = f(token_value)
                        except:
                            Raise.code_error(f"Supplied callback has no callable function for {rule.type}")

                new_token = Token2(rule.type, token_value, line_number)
                tokens.append(new_token)

            text = text[match_len :]
            if match_len == 0:
                Raise.code_error(f"Error: no regex matches, head of input: {text[0:10]}")

        return tokens
