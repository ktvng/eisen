def indent(txt: str) -> str:
    indent = "    ";
    level = 0

    parts = txt.split("\n")
    formatted_txt = ""
    for part in parts:
        level -= part.count('}')
        formatted_txt += indent*level + part + "\n"
        level += part.count('{')

    return formatted_txt