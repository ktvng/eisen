from __future__ import annotations

import re

class formatter:
    # max number of characters which can appear on a line (not including the indent 
    # at the beginning of the line, or any closing parentheses from earlier statements)
    max_line_size = 64

    # string to use for the indent at the beginning of a line
    indent_str = "  "

    # matches strings
    str_regex = re.compile(r"([\"'])(?:(?=(\\?))\2.)*?\1")

    # matches any content (not strings and not list denotations)
    content_regex = re.compile(r"[^\(\)\"']+")

    # matches one or more list closure paren and any whitespace inbetween successive 
    # list closures
    list_end_regex = re.compile(r"\)")
    
    @classmethod
    def _chunk_with_balanced_parens(cls, clr: str) -> tuple[str, str]:
        provided_clr = clr
        if not clr:
            return "", ""
        if clr[0] != "(":
            raise Exception(f"clr expected to begin with L-parens '(' but got {clr}")

        # remove the leading "(" and add it to the chunk
        chunk = clr[0]
        clr = clr[1:]

        # paren depth now starts at 1
        paren_depth = 1
        while clr and paren_depth != 0:
            match = cls.str_regex.match(clr)
            if not match:
                match = cls.content_regex.match(clr)

            # if here, then the head must be either '(' or ')'
            if not match:
                if clr[0] == "(":
                    chunk += "("
                    paren_depth += 1
                elif clr[0] == ")":
                    chunk += ")"
                    paren_depth -= 1
                else:
                    raise Exception(f"unexpected value found in clr {clr}")

                # remove the leading paren and continue 
                clr = clr[1:]
                continue
            
            matched = match.group(0)
            chunk += matched
            clr = clr[len(matched):]

        if paren_depth != 0:
            raise Exception(f"provided clr does not have balanced parens? {provided_clr}")
        return chunk, clr

    @classmethod
    def _count_net_parens_depth(cls, s: str) -> int:
        return s.count("(") - s.count(")")

    @classmethod
    def format_clr(cls, clr: str) -> str:
        level = 0
        formatted_clr = ""
        while clr:
            # any non-list (token) content at the head of a list will be appended at the 
            # correct indent level
            match = cls.content_regex.match(clr)
            if match:
                content = match.group(0)
                formatted_clr += content
                clr = clr[len(content): ]
                continue

            # flush any end parens
            match = cls.list_end_regex.match(clr)
            if match:
                content = match.group(0)
                formatted_clr += content
                level += cls._count_net_parens_depth(content)
                clr = clr[len(content): ]
                continue

            # try to get the next well formatted chunk
            chunk, rest = cls._chunk_with_balanced_parens(clr)
            if len(chunk) > cls.max_line_size:
                formatted_clr += "\n" + cls.indent_str * level + "("
                level += 1
                clr = clr[1:]
                continue
            else:
                formatted_clr += "\n" + cls.indent_str * level + chunk
                clr = rest 
            
        # remove the "\n" at the beginning
        return formatted_clr[1:]

    @classmethod
    def indent(cls, txt: str) -> str:
        indent = "    ";
        level = 0

        parts = txt.split("\n")
        formatted_txt = ""
        for part in parts:
            level -= part.count('}')
            formatted_txt += indent*level + part + "\n"
            level += part.count('{')

        return formatted_txt