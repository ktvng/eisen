from __future__ import annotations
import re

class TokenRule():
    def __init__(self, regex: str, type_chain: list[str]):
        self.regex_str = regex
        self.regex = re.compile(regex)
        self.type_chain = type_chain[::-1]
        self.type = self.type_chain[0]

    def __str__(self) -> str:
        type_str = " ".join(self.type_chain[::-1])
        return f"{type_str} -> {self.regex_str}"

    def match(self, txt: str) -> tuple[str, int, TokenRule]:
        match = self.regex.match(txt)
        if match:
            return match.group(0), len(match.group(0)), self
        return "", 0, self

    def is_classified_as(self, type: str) -> bool:
        return type in self.type_chain
