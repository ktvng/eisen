from __future__ import annotations
import re

class RegexTokenRule():
    def __init__(self, regex : str, type : str, value : str=None):
        self.regex_str = regex
        self.regex = re.compile(regex)
        self.type = type
        self.value = value

    def __str__(self):
        return f"[{self.regex_str}] -> {self.type} {self.value}"

    def match(self, text : str):
        match_obj = self.regex.match(text)
        if match_obj:
            match_str = match_obj.group(0)
            return match_str, len(match_str), self

        return "", 0, self