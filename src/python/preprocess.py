from __future__ import annotations

class Preprocessor:
    @classmethod
    def run(cls, txt: str) -> str:
        indent = None
        indent_level = 0
        new_lines = []
        for line in txt.split("\n"):
            if not line.strip():
                new_lines.append(line)
                continue

            if indent is None:
                indent = Preprocessor.get_indent_token(line)
            new_indent_level = Preprocessor.get_indent_level(line, indent)
            if indent:
                for i in range(indent_level, new_indent_level):
                    new_lines.append(indent*i + "{")
                ends = []
                for i in range(new_indent_level, indent_level):
                    ends = [indent*i + "}"] + ends
                new_lines += ends
            new_lines.append(line)
            indent_level = new_indent_level
        if indent:
            for i in range(indent_level-1, -1, -1):
                new_lines.append(indent*i + "}")
        return "\n".join(new_lines)

    @classmethod
    def get_indent_token(cls, line: str) -> str:
        indent = None
        if line[0] == " ":
            indent = ""
            while line[0] == " ":
                indent += " "
                line = line[1:]
        return indent

    @classmethod
    def get_indent_level(cls, line: str, indent_token: str) -> int:
        if indent_token is None:
            return 0
        indent_level = 0
        while line.startswith(indent_token):
            indent_level += 1
            line = line[len(indent_token):]
        return indent_level
