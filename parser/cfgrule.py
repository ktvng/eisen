from __future__ import annotations
from parser.action import Action

class CFGRule():
    def __init__(self, production_symbol : str, pattern_str : str, action : Action):
        self.production_symbol = production_symbol
        self.pattern_str = pattern_str
        self.pattern = [s.strip() for s in pattern_str.split(' ') if s != ""]

        if isinstance(action, list):
            self.actions = action
            self.reverse_with = action
        else:
            
            self.actions = [action]
            # TODO: replace with above; here for back-compat
            self.reverse_with = [action]

    def __str__(self):
        return f"{self.production_symbol} -> {self.pattern_str}"

    @classmethod
    def is_production_symbol(cls, token : str):
        return token.isupper() and all(map(lambda x : x.isalnum() or x == '_', token))



class GrammarRule():
    """
    Encapsulates the information of a CFG production rule, including a string/list of strings which
    encodes how the rule should be reversed
    """
    def __init__(self, production_symbol : str, pattern_str : str, reverse_with : str | list[str]):
        """
        Create a new GrammarRule.

        Args:
            production_symbol (str): symbol which produces the pattern
            pattern_str (str): pattern which can be produced from the production_symbol
            reverse_with (str | list[str]): string(s) which define which methods to use to reverse
                                            the rule
        """
        self.production_symbol = production_symbol.strip()
        self.pattern_str = pattern_str
        self.pattern = [s.strip() for s in pattern_str.split(' ') if s != ""]

        if isinstance(reverse_with, str):
            self.reverse_with = [reverse_with]
        elif isinstance(reverse_with, list):
            self.reverse_with = reverse_with

    @classmethod
    def is_production_symbol(cls, token : str):
        return token.isupper() and all(map(lambda x : x.isalnum() or x == '_', token))

    def __str__(self):
        return self.production_symbol + " -> " + self.pattern_str