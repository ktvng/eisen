from __future__ import annotations

import re

from alpaca.config._config import Config
from alpaca.clr._clr import CLRList, CLRToken

class CLRParser():
    @classmethod
    def run(cls, config: Config, txt: str) -> CLRList | CLRToken:
        lst = cls.unpack_single_layer(txt)
        objs = []
        for elem in lst[1:]:
            if cls.is_list_itself(elem):
                objs.append(CLRParser.run(config, elem))
            else:
                longest_match, longest_len, longest_rule = None, 0, None
                for rule in config.regex_rules:
                    match_str, len, rule = rule.match(elem)
                    if match_str and len > longest_len:
                        longest_match, longest_len, longest_rule = match_str, len, rule

                if longest_match is None:
                    raise Exception(f"no match for {elem}")
                objs.append(CLRToken(longest_rule.type_chain, longest_match, 0))
        return CLRList(lst[0], objs)

    @classmethod
    def is_list_itself(cls, txt: str):
        return "(" == txt.strip()[0]

    word_regex = r"[^\s]+"
    space_regex = r"\s+"
    string_regex  = r"([\"'])(?:(?=(\\?))\2.)*?\1"
    @classmethod
    def unpack_single_layer(cls, txt: str) -> list[str]:
        parts = []
        txt = txt.strip()[1:-1].strip()
        while txt:
            match = re.match(cls.space_regex, txt)
            if match:
                txt = txt[len(match.group(0)):]
                continue

            match = re.match(cls.string_regex, txt)
            if match:
                part = match.group(0)
                parts.append(part)
                txt = txt[len(part):]
                continue

            if txt[0] == "(":
                idx = 1
                net_parens = 1
                while net_parens != 0 and idx < len(txt):
                    if txt[idx] == "(":
                        net_parens += 1
                    elif txt[idx] == ")":
                        net_parens -= 1
                    idx += 1

                part = txt[0 : idx]
                parts.append(part)
                txt = txt[len(part):]
                continue

            match = re.match(cls.word_regex, txt)
            if match:
                part = match.group(0)
                parts.append(part)
                txt = txt[len(part):]
                continue

        return parts
